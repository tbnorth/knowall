"""
knowall.py - recursively stat a directory, dump results,
analyze dumped results

Terry Brown, terrynbrown@gmail.com, Fri Jun 24 15:28:45 2016
"""

import argparse
import csv
import json
import os
import re
import sqlite3
import stat
import sys
import time
from collections import defaultdict, namedtuple
from datetime import datetime
from functools import lru_cache
from hashlib import sha1
from types import SimpleNamespace

try:
    import folderstats
    import pandas as pd
except ImportError:
    pass  # fail later, not needed for most operations
from dateutil.parser import parse

EPOCH = datetime(1970, 1, 1)

FileInfo = namedtuple(
    "FileInfo",
    "name st_mode st_ino st_dev st_nlink st_uid "
    "st_gid st_size st_atime st_mtime st_ctime",
)
# when windows max file length causes os.lstat() to fail, use this
NULLSTAT = tuple([None] * (len(FileInfo._fields) - 1))  # list above minus name

# strings are used as keys for directories in get_hier_db() and
# dupe_dirs(), so these are non-string keys for non-directory items
FILES = 1
CHILD_HASH = 2
CHILD_FILES = 3
CHILD_BYTES = 4

# build list of modes available
MODES = {}

SORTS = {
    "name": "Force alphabetical sorting, unsorted may be alphabetical and faster",
    "count": "Sort dirs / dupes by file count (dupes defaults to total size)",
    "size": "Sort dirs by size",
    "length": "Sort by path length",
}


def mode(func):
    """mode - decorator to collect modes

    :param function func: function to add to list
    """

    MODES[func.__name__] = func
    return func


def uni(t):
    return t.decode("cp1252") if isinstance(t, bytes) else t


class Formatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter,
):
    pass


def make_parser():
    """
    make_parser - make an argparse.ArgumentParser

    :return: parser
    :rtype: argparse.ArgumentParser
    """

    description = [
        "Recursively stat files. e.g.\n",
        "    # first collect data\n"
        "    python knowall.py --top-dir some/path > some_path.json\n"
        "    # then analyze - 5 largest dupes.\n"
        "    python < some_path.json --mode dupes --show-n 5 \n"
        "    # most common extensions on subpath\n"
        "    python < some_path.json --mode rank_ext --path-filter some/path/here\n\n"
        "Modes:",
    ]

    for mode in MODES.values():
        description.append(
            "% 12s: %s" % (mode.__name__, mode.__doc__.split("\n", 1)[0])
        )
    description.append("\nSort types [ONLY --mode dirs --sort length IMPLEMENTED]:")
    for type_, text in SORTS.items():
        description.append(f"{type_:>12}: {text}")
    parser = argparse.ArgumentParser(
        description="\n".join(description), formatter_class=Formatter
    )

    modenames = list(MODES)

    def mode_check(x):
        if x not in modenames:
            raise argparse.ArgumentTypeError("%s not in %s" % (x, modenames))
        return x

    group = parser.add_argument_group("required arguments")
    group.add_argument(
        "--mode",
        default=modenames[0],
        help="mode from list above",
        type=mode_check,
    )

    parser.add_argument(
        "--top-dir", default=".", help="path to start from", metavar="DIR"
    )
    parser.add_argument(
        "--show-n",
        type=int,
        default=0,
        help="show this many results in summaries, 0 == all",
        metavar="N",
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        help="extensions to list in find_ext mode",
        metavar="EXT",
        default=["jpg", "dat", "txt"],
    )
    parser.add_argument(
        "--min-size",
        metavar="BYTES",
        type=int,
        help="ignore files smaller than this size",
    )
    parser.add_argument(
        "--max-size",
        metavar="BYTES",
        type=int,
        help="ignore files larger than this size",
    )
    parser.add_argument(
        "--path-filter",
        metavar="REGEX",
        help="regular expression paths must match, case insensitive",
    )
    parser.add_argument(
        "--file-filter",
        metavar="REGEX",
        help="regular expression files must match, case insensitive. "
        "Use '^(?!.*<pattern>)' to exclude <pattern>, e.g. "
        '--file-filter "^(?!.*(jpg|dat))"',
    )
    parser.add_argument(
        "--ignore-hidden",
        metavar="BOOL",
        help="folderstats mode to ignore hidden files or not",
        type=bool,
        default=True,
    )
    parser.add_argument(
        "--out-file",
        metavar="FILE",
        help="folderstats mode filename or path to save output to CSV",
        type=str,
        default="folderstats_mode_output.csv",
    )

    for type_ in "creation", "modification", "access":
        parser.add_argument(
            "--min-%stime" % type_[0],
            help="Minimum %s time" % type_,
            metavar="TIME",
        )
        parser.add_argument(
            "--max-%stime" % type_[0],
            help="Maximum %s time, free format, e.g. YYYYMMDDHHMM" % type_,
            metavar="TIME",
        )
    parser.add_argument(
        "--show-time",
        help="Any combination of 'C', 'M', 'A', e.g. MA, times " "to show in file mode",
        metavar="TIMES",
    )

    parser.add_argument(
        "--dupes-sort-n",
        default=False,
        action="store_true",
        help="sort dupe listing by count, not size",
    )
    parser.add_argument(
        "--dupes-no-hash",
        default=False,
        action="store_true",
        help="don't hash possible dupes to check content, "
        "just use size.  WARNING: may return false dupe listings."
        "NOTE: does not calc. *new* hashes, will still use hashes from --hash-db",
    )
    parser.add_argument(
        "--hash-db",
        help="SQLite DB of hash values to check/update before/when hashing",
    )
    parser.add_argument(
        "--resume-from",
        metavar="PATH",
        help="skip paths before (alphabetically) PATH to resume interrupted indexing",
    )
    parser.add_argument(
        "--sort",
        metavar="TYPE",
        help="Type of sorting, from list above.",
    )
    parser.add_argument(
        "--reverse",
        help="Reverse sorting.",
        default=False,
        action="store_true",
    )

    return parser


def get_options(args=None):
    """
    get_options - process arguments

    :param [str] args: list of arguments
    :return: options
    :rtype: argparse.Namespace
    """
    opt = make_parser().parse_args(args)
    opt.extensions = [i.upper() for i in opt.extensions]
    for attr in "file", "path":
        regex = getattr(opt, attr + "_filter")
        if regex:
            setattr(opt, attr + "_filter", re.compile(regex, flags=re.IGNORECASE))
    # convert time text to time
    for end in "min", "max":
        for type_ in "cma":  # ctime, mtime, atime - create, modify, access
            text = "%s_%stime" % (end, type_)
            if getattr(opt, text):
                try:
                    timestamp = int((parse(getattr(opt, text)) - EPOCH).total_seconds())
                    setattr(opt, text, timestamp)
                except Exception:
                    print("Failed parsing %s '%s'" % (text, getattr(opt, text)))
                    raise
    return opt


def correctSingleQuoteJSON(s):
    """Correct single quote strings to correct JSON format expecting double quote
    Helper function from: https://stackoverflow.com/questions/47659782/python-how-
    convert-single-quotes-to-double-quotes-to-format-as-json-string
    """
    rstr = ""
    escaped = False

    for c in s:

        if c == "'" and not escaped:
            c = '"'  # replace single with double quote
        elif c == "'" and escaped:
            rstr = rstr[:-1]  # remove escape character before single quotes
        escaped = c == "\\"  # check for an escape character
        rstr += c  # append the correct json
    return rstr


def convert_input_file(inFile):
    """convert_input_file - Check input file type and convert to expected JSON

    :param sys.stdin <_io.TextIOWrapper name='<stdin>' mode='r' encoding='cp1252'>
    inFile: command line redirected input (<)

    """
    try:  # Read first line and check if JSON
        json.loads(inFile.readline())
        inFile.seek(0)  # Reset back to line 0
        return inFile
    except Exception:  # If lines aren't JSON, then try CSV
        try:
            inFile.seek(0)  # Reset back to line 0
            in_dat = pd.read_csv(inFile)
        except Exception:  # Only allow JSON or CSV input at this time
            print("...Error...Input file is not JSON or CSV")
            raise
        # Reformat input CSV into JSON format
        # Format 'path' column as an acceptable path string
        # https://stackoverflow.com/questions/65910282/jsondecodeerror-invalid-escape-when-parsing-from-python
        regList = {r"([^\\])\\([^\\])": r"\1\\\\\2", r",(\s*])": r"\1"}

        in_dat["path"] = in_dat["path"].replace(regList, regex=True)
        # Rename columns
        in_dat = in_dat.rename(
            columns={
                "name": "name",
                "uid": "st_uid",
                "size": "st_size",
                "atime": "st_atime",
                "mtime": "st_mtime",
                "ctime": "st_ctime",
            }
        )

        # Add missing column(s) as empty 0 (nn lamba function)
        in_dat[list(set(FileInfo._fields) - set(in_dat.columns))] = 0

        # Convert time columns from text to numeric (based on get_options() logic)
        # in_dat = in_dat.apply(lambda x: int((parse(x) - EPOCH).total_seconds()) if
        # x.name in ['st_atime', 'st_mtime', 'st_ctime'] else x)
        in_dat["st_atime"] = in_dat["st_atime"].apply(
            lambda x: int((parse(x) - EPOCH).total_seconds())
        )
        in_dat["st_mtime"] = in_dat["st_mtime"].apply(
            lambda x: int((parse(x) - EPOCH).total_seconds())
        )
        in_dat["st_ctime"] = in_dat["st_ctime"].apply(
            lambda x: int(
                (
                    parse(
                        x,
                    )
                    - EPOCH
                ).total_seconds()
            )
        )

        # Get list of directory paths
        in_dirs = in_dat.loc[in_dat["folder"]].copy()
        # Get just files (not directories)
        in_files = in_dat.loc[~in_dat["folder"]].copy()
        del in_dat
        # Fill nan extension with empty string
        in_files["extension"] = in_files["extension"].fillna("")
        # Combine name and extension columns
        in_files["name"] = in_files["name"] + "." + in_files["extension"]
        # Create dictionary of files by directory paths
        # in_dat.loc[in_dat.parent == in_dirs.id[x]]
        inFile = {
            in_dirs.path[x]:
            # Convert dataframe rows to list of lists
            [
                row.tolist()
                for i, row in in_files[list(FileInfo._fields)]
                .loc[in_files.parent == in_dirs.id[x]]
                .iterrows()
            ]
            for x in in_dirs.index
        }
        # Convert to JSON list
        inFile = [
            correctSingleQuoteJSON(
                r'{"path": ' + rf'"{str(key)}", "files":{str(value)}}}'
            )
            for key, value in inFile.items()
        ]
        return inFile


def get_data(opt):
    """get_data - generator, read data, applying filters

    :param argparse.Namespace opt: command line options
    """

    filtered = any(
        [
            opt.file_filter,
            opt.max_size,
            opt.min_size,
            opt.min_atime,
            opt.min_ctime,
            opt.min_mtime,
            opt.max_atime,
            opt.max_ctime,
            opt.max_mtime,
        ]
    )

    nn = lambda x: x if x is not None else 0
    # Check/Handle Input file Format to JSON
    stdin = convert_input_file(sys.stdin)
    for line in stdin:
        try:
            data = json.loads(line)
        except json.decoder.JSONDecodeError:
            sys.stderr.write("Rejected for encoding issue:\n")
            sys.stderr.write(f"{line}\n")
            continue
        data["files"] = [FileInfo._make(i) for i in data["files"]]
        if opt.path_filter and not opt.path_filter.search(data["path"]):
            continue
        data["files"] = [
            i
            for i in data["files"]
            if (opt.max_size is None or nn(i.st_size) <= opt.max_size)
            and (opt.min_size is None or nn(i.st_size) >= opt.min_size)
            and (opt.file_filter is None or opt.file_filter.search(i.name))
            and (opt.min_atime is None or nn(i.st_atime) >= opt.min_atime)
            and (opt.max_atime is None or nn(i.st_atime) <= opt.max_atime)
            and (opt.min_ctime is None or nn(i.st_ctime) >= opt.min_ctime)
            and (opt.max_ctime is None or nn(i.st_ctime) <= opt.max_ctime)
            and (opt.min_mtime is None or nn(i.st_mtime) >= opt.min_mtime)
            and (opt.max_mtime is None or nn(i.st_mtime) <= opt.max_mtime)
        ]
        if data["files"] or not filtered:
            yield data


def get_flat_db(opt):
    """get_flat_db - get flat dir: paths dict

    :param argparse.Namespace opt: command line options
    :rtype: dict
    """

    db = {}

    for data in get_data(opt):
        db[data["path"]] = data["files"]
    return db


def get_hier_db(opt):
    """get_hier_db - get hierarchical dir: paths dict

    FILES == 1, a non-string and therefore non-directory name key

    Input:
        {"path": "/a", "files": ["x", "y"]},
        {"path": "/a/b", "files": ["x", "z"]},
        {"path": "/a/b/c", "files": ["z", "y"]},
    Output:
        {1: [], 'a': {1: ['x', 'y'], 'b': {1: ['x', 'z'], 'c': {1: ['z', 'y']}}}}
        i.e. a root with no files and one dir, 'a', which has two files and one dir 'b',
        etc. etc.

    Args:
        opt (argparse.Namespace): options

    Returns:
        dict: hierarchical dict
    """

    db = {FILES: []}

    for data in get_data(opt):
        insert = db  # reset to top
        for path in data["path"].strip("/").split("/"):
            if path not in insert:
                insert[path] = {FILES: []}
            insert = insert[path]
        # files list from data goes in leaf node
        insert[FILES] = data["files"]
    return db


def path_length_check(path):
    """path_length_check - check if file can be found, if not, add prefix and check
    :param str path: path to file
    :return fixed filepath after checking if file exists (add prefix to long paths)
    :rtype: str

    """
    # https://stackoverflow.com/questions/29557760/long-paths-in-python-on-windows
    prefix = "\\\\?\\"
    # prefix = r"\\?\UNC" #Prefix to allow long file paths to work
    if os.path.isfile(path):  # File found as-is
        return path
    elif os.path.isfile(prefix + path):  # File found with prefix
        return prefix + path
    else:  # File can't be found, even with prefix, return None
        return None


def get_hash(path, callback=None):
    """get_hash - get hash for file

    :param str path: path to file
    :param function(read) callback: callback for progress updates
    :return: sha1 hash of file
    :rtype: str
    """

    buff_size = 10000000
    import hashlib

    digest = hashlib.sha1()
    if path:
        infile = open(long_path(path), "rb")
    else:
        # probably the Windows path length issue again
        return "NOFILEACCESS"
    read = 0
    while True:
        data = infile.read(buff_size)
        read += len(data)
        if callback:
            callback(read)
        digest.update(data)
        if len(data) != buff_size:
            break
    return digest.hexdigest()


def long_path(path: str) -> str:
    """Prependspecial prefixes to make long paths work in Windows"""
    if len(path) < 3:  # "." etc.
        return path
    if path[0] == "\\":  # Windows \\sharename\path
        path = path.lstrip("\\")
        return f"\\\\?\\UNC\\{path}"
    elif path[1] == ":":  # Windows C:/path/here
        return f"\\\\?\\{path}"
    else:
        return path


@mode
def recur_stat(opt):
    """Recursively stat folder, store this output for other modes

    :param argparse.Namespace opt: command line options
    """
    count = 0
    active = False if opt.resume_from else True
    for path, dirs, files in os.walk(opt.top_dir):
        if not active:
            if path != opt.resume_from:
                sys.stderr.write(f"Skipping '{path}'\n")
                if not opt.resume_from.startswith(path):
                    dirs[:] = []
                continue
            active = True
        out = {"path": uni(path), "files": []}
        for filename in files:
            filepath = os.path.join(path, filename)
            filepath = path_length_check(filepath)
            if filepath:  # Check if filepath is None (path_length_check failed)
                count += 1
                out["files"].append(
                    tuple([uni(filename)]) + tuple(os.lstat(long_path(filepath)))
                )
            else:  # hit Windows max path length
                filepath = os.path.abspath(os.path.join(path, filename))
                sys.stderr.write(f"Can't open {len(filepath)} char. path {filepath}\n")
                out["files"].append(tuple([uni(filename)]) + NULLSTAT)
        print(json.dumps(out))
        sys.stderr.write("%d %s\n" % (count, path))


@mode
def find_ext(opt):
    """Find folders with files with listed extensions

    :param argparse.Namespace opt: command line options
    """
    exts = defaultdict(lambda: defaultdict(lambda: 0))

    for data in get_data(opt):

        for fileinfo in data["files"]:
            name, ext = os.path.splitext(fileinfo.name)
            exts[ext.upper()][data["path"]] += 1
    pathcount = defaultdict(lambda: defaultdict(lambda: 0))

    for ext in opt.extensions:
        for path in exts["." + ext]:
            pathcount[path][ext] = exts["." + ext][path]
    writer = csv.writer(sys.stdout)
    writer.writerow(opt.extensions + ["path"])
    order = sorted(
        pathcount, key=lambda path: sum(pathcount[path].values()), reverse=True
    )
    for n, path in enumerate(order):
        row = [str(pathcount[path][i]) for i in opt.extensions] + [path]
        writer.writerow(row)
        if opt.show_n and n + 1 >= opt.show_n:
            break


@mode
def rank_ext(opt):
    """Rank extensions by popularity

    :param argparse.Namespace opt: command line options
    """

    counts = ranked_extensions(opt)

    for i in counts[: opt.show_n] if opt.show_n else counts:
        print("% 5d %s" % tuple(i))


def ranked_extensions(opt):

    exts = defaultdict(lambda: defaultdict(lambda: 0))

    for data in get_data(opt):

        for fileinfo in data["files"]:
            name, ext = os.path.splitext(fileinfo.name)
            exts[ext.upper()][data["path"]] += 1
            exts[ext.upper()]["__COUNT"] += 1
    counts = [[exts[i]["__COUNT"], i] for i in exts]
    counts.sort(reverse=True)
    return counts


@mode
def summary(opt):
    """Summary of files in data

    :param argparse.Namespace opt: command line options
    """

    statistics = stats(opt)
    print(
        "{dirs:,d} folders, {files:,d} files, {bytes:,d} bytes, "
        "no stats. {nostat:,d}".format_map(statistics)
    )


def stats(opt):
    res = defaultdict(int)

    for data in get_data(opt):

        res["dirs"] += 1

        for fileinfo in data["files"]:
            res["files"] += 1
            if fileinfo.st_size is None:
                res["nostat"] += 1
            else:
                res["bytes"] += fileinfo.st_size
    return res


def sort_function(opt, subtype):
    """Return a function for sorting output, X in a_list.sort(key=X).

    Args:
        opt (argparse opts): options incl. opt.sort (str)
        subtype (str): dirs, files, dupes - type of thing being sorted

    Returns:
        function: function to get key from item
    """
    if opt.sort == "length":
        return lambda x: len(x["path"])


@mode
def dirs(opt):
    """Dumps dirs

    :param argparse.Namespace opt: command line options
    """

    if not opt.sort:
        for n, data in enumerate(get_data(opt)):
            print(data["path"])
            if opt.show_n and n + 1 >= opt.show_n:
                break
        return
    all_data = list(get_data(opt))
    all_data.sort(key=sort_function(opt, "dirs"), reverse=opt.reverse)
    for n, data in enumerate(all_data):
        print(data["path"])
        if opt.show_n and n + 1 >= opt.show_n:
            break


@mode
def files(opt):
    """Dumps files

    :param argparse.Namespace opt: command line options
    """

    for file_ in list_files(opt):
        print(file_)


def list_files(opt):
    count = 0
    for data in get_data(opt):
        for fileinfo in data["files"]:
            text = os.path.join(data["path"], fileinfo.name)
            for i in opt.show_time or []:
                x = {
                    "a": fileinfo[stat.ST_ATIME + 1],
                    "c": fileinfo[stat.ST_CTIME + 1],
                    "m": fileinfo[stat.ST_MTIME + 1],
                }.get(i.lower())
                if x:
                    text += " " + time.ctime(x)
            yield text
            count += 1
            if opt.show_n and count == opt.show_n:
                return


@lru_cache()
def hash_db_con_cur(dbpath):
    """Return connection to hash db, creating if necessary"""

    if not dbpath:
        return None, None
    existed = os.path.exists(dbpath)
    con = sqlite3.connect(dbpath)
    cur = con.cursor()
    if not existed:
        cur.execute(
            "create table hash (" "filepath text, st_size int, st_mtime int, hash text)"
        )
        cur.execute(
            "create unique index hash_filepath_idx on "
            "hash(filepath, st_size, st_mtime)"
        )
        con.commit()
    cur.execute("PRAGMA main.synchronous = OFF")
    return con, cur


@lru_cache()
def find_hash(dbpath, filepath, fileinfo, no_hash=False):
    """Find the hash for filepath, depending on hashing settings

    Storing file hashes to determine true duplicates is really just intended as
    a chaching mechanism to speed up repeated duplicate analysis on the same
    JSON index file.  I.e. ideally the hash cache DB would be deleted when a
    new JSON index file is created.  But, on slow links, reusing the hash cache
    DB could save a lot of time, for that reason the hash index includes file
    size and modification time as well as path.
    """
    hashtext = None
    con, cur = hash_db_con_cur(dbpath)
    if con:
        cur.execute(
            "select hash from hash where filepath = ? "
            " and st_size = ? and st_mtime = ?",
            [filepath, fileinfo.st_size, fileinfo.st_mtime],
        )
        hashtexts = cur.fetchall()
        if hashtexts:
            hashtext = hashtexts[0][0]
    if hashtext or no_hash:
        return hashtext or "no-hash"

    def callback(read, filepath=filepath, fileinfo=fileinfo, __last=[time.time()]):
        if time.time() - __last[0] > 10:
            pct = 100 * read / fileinfo.st_size
            print(f"{filepath}: {read:,d}/{fileinfo.st_size:,d} {pct:.1f}%")
            __last[0] = time.time()

    hashtext = get_hash(filepath, callback=callback)
    con, cur = hash_db_con_cur(dbpath)
    if con:
        cur.execute(
            "insert into hash values (?, ?, ?, ?)",
            [filepath, fileinfo.st_size, fileinfo.st_mtime, hashtext],
        )
        con.commit()
    return hashtext


def get_dupes(opt):
    """Find duplicate files

    :param argparse.Namespace opt: command line options
    """

    # group by size
    sizes = defaultdict(lambda: [])
    for data in get_data(opt):
        for filedata in data["files"]:
            fileinfo = FileInfo(*filedata)
            sizes[fileinfo.st_size].append((data["path"], fileinfo))
    # sort by size or count
    if opt.dupes_sort_n:
        order = sorted(sizes, reverse=True, key=lambda x: len(sizes[x]))
    else:
        order = sorted(sizes, reverse=True, key=lambda x: x or 0)
    for size in order:
        if len(sizes[size]) < 2:
            continue
        # within sizes with multiples, hash files, maybe
        hashed = defaultdict(list)
        for path, fileinfo in sizes[size]:
            filepath = os.path.join(path, fileinfo.name)

            hashtext = find_hash(
                opt.hash_db, filepath, fileinfo, no_hash=opt.dupes_no_hash
            )
            # can't yield this yet, reference to single file that may not be
            # a dupe
            hashed[(size, hashtext)].append(filepath)
        # now filter out singles and yield dupes
        yield {k: v for k, v in list(hashed.items()) if len(v) > 1}


@mode
def dupes(opt):
    """Print duplicate files

    :param argparse.Namespace opt: command line options
    """
    n = 0
    stats = defaultdict(lambda: 0)
    for hashed in get_dupes(opt):
        stats["sizealts"] = max(stats["sizealts"], len(hashed))
        stats["sizedupes"] = max(
            stats["sizedupes"], sum(len(i) - 1 for i in hashed.values())
        )
        for (size, hash), files in hashed.items():
            size = size or 0  # can be None for unstatable files
            files_n = len(files)
            assert files_n > 1
            stats["files"] += files_n - 1
            stats["bytes"] += (files_n - 1) * size
            stats["largest"] = max(stats["largest"], size)
            stats["mostdupes"] = max(stats["mostdupes"], files_n - 1)
            stats["mostspace"] = max(stats["mostspace"], (files_n - 1) * size)

            if len(hashed) > 1:  # same size, multiple contents (hashes)
                sizetext = f"{size or 0:,d}:{hash}"
            else:  # same content for all
                sizetext = f"{size or 0:,d}"
            print(sizetext, files_n, files)
            n += 1
        # might overshoot, but better to show complete sets of dupes
        if opt.show_n and n >= opt.show_n:
            break
    for k, v in stats.items():
        print(f"{k:>12s}: {v:,d}")


def recur(state, node, path):
    """Use size for initial pass, real hash later."""

    state.path_node[path] = node

    child_hashes = []
    child_total = 0
    child_bytes_total = 0

    for key in node:
        if not isinstance(key, int):
            child_hash, child_count, child_bytes = recur(
                state, node[key], os.path.join(path, key)
            )
            if child_count:
                child_hashes.append(child_hash)
                child_total += child_count
                child_bytes_total += child_bytes
    for fileinfo in sorted(node[FILES]):
        if fileinfo.st_size is None:
            continue  # happens when Windows path length limit breaks things
        if mode == "size":
            child_hashes.append(fileinfo.st_size)
        else:
            child_path = os.path.join(path, fileinfo.name)
            hashtext = find_hash(
                state.opt.hash_db,
                child_path[1:],
                fileinfo,
                no_hash=state.opt.dupes_no_hash,
            )
            child_hashes.append(hashtext)
        child_total += 1
        child_bytes_total += fileinfo.st_size
    node[CHILD_HASH] = get_list_hash(child_hashes)
    node[CHILD_FILES] = child_total
    node[CHILD_BYTES] = child_bytes_total
    state.hashes[(child_bytes_total, node[CHILD_HASH])].append(path)

    return node[CHILD_HASH], child_total, child_bytes_total


@mode
def dupe_dirs(opt):
    """Find duplicate dirs., list from largest to smallest

    :param argparse.Namespace opt: command line options
    """

    state = SimpleNamespace()
    state.opt = opt
    state.mode = "size"
    state.hashes = defaultdict(lambda: list())
    state.path_node = {}

    db = get_hier_db(opt)

    recur(state, db, "/")
    state.mode = "hash"  # For subsequent calls

    hash_sizes = sorted(state.hashes, reverse=True)
    shown = 0
    seen = set()
    for size, child_hash in hash_sizes:
        if len(state.hashes[(size, child_hash)]) < 2:
            continue
        # Get actual hash for each in list
        size_hashes = defaultdict(list)
        for path in list(state.hashes[(size, child_hash)]):
            if any(path.startswith(i) for i in seen):
                continue
            path_hash, _, _ = recur(state, state.path_node[path], path)
            size_hashes[path_hash].append(path)
        for hash, paths in size_hashes.items():
            if len(paths) < 2:
                continue
            print(f"{size:,}")
            for i in paths:
                print(i)
                seen.add(i)
            print()
        shown += 1
        if opt.show_n and shown >= opt.show_n:
            break


def get_list_hash(hash_list):
    """get_list_hash - get a hash for a list of hashes

    :param list hash_list: list of hashes
    :return: a hash
    :rtype: str
    """

    return sha1(str(hash_list).encode("utf8")).hexdigest()


def variants_add_hashes(opt, paths):
    if len(paths) <= 1:
        return [i + ("",) for i in paths]
    ans = []
    for path, fileinfo in paths:
        filepath = os.path.join(path, fileinfo.name)
        hashtext = find_hash(
            opt.hash_db,
            filepath,
            fileinfo,
            no_hash=opt.dupes_no_hash,
        )
        ans.append((path, fileinfo, hashtext[:7] + " "))
    return ans


def timestamp_text(ts):
    return time.strftime("%Y%m%d%H%M%S", time.localtime(ts))


@mode
def variants(opt):
    """List variant files (same name, different content)"""
    name = defaultdict(list)
    for data in get_data(opt):
        for fileinfo in data["files"]:
            name[fileinfo.name].append((data["path"], fileinfo))
    for filename, paths in name.items():
        if len(paths) == 1:
            continue
        print(filename)
        sizes = defaultdict(list)
        for path, fileinfo in paths:
            sizes[fileinfo.st_size].append((path, fileinfo))
        for size, paths in sizes.items():
            print(f"    {size:,d} ")
            paths = variants_add_hashes(opt, paths)
            for path, fileinfo, hash in paths:
                print(f"        {hash}{timestamp_text(fileinfo.st_ctime)} {path}")


@mode
def folderstats_pkg(opt):
    """Recursively pull stats for all folders within an input path
    using the folderstats package. This package works fast due to recursion
    and handles long paths (Windows limitation) through the use of os.scandir.

    Links:
        https://github.com/njanakiev/folderstats
        https://bugs.python.org/issue33105 (see msg314126 Author: Eryk Sun (eryksun)
        Date: 2018-03-20 01:12)

    :param argparse.Namespace opt: command line options
    :return: pandas dataframe of folderstats output
    """
    df = folderstats.folderstats(opt.top_dir, ignore_hidden=opt.ignore_hidden)
    # Export analysis
    df.to_csv(opt.out_file)
    return df


def main():
    """main - get options and dispatch mode"""
    opt = get_options(sys.argv[1:])
    start = time.time()
    globals()[opt.mode](opt)
    sys.stderr.write("%.2g seconds\n" % (time.time() - start))


if __name__ == "__main__":
    main()
