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
import sys

from collections import defaultdict, namedtuple

if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

FileInfo = namedtuple("FileInfo",
    'name st_mode st_ino st_dev st_nlink st_uid '
    'st_gid st_size st_atime st_mtime st_ctime')

MODES = []
def mode(func):
    """mode - decorator to collect modes

    :param function func: function to add to list
    """

    MODES.append(func)
    return func
def uni(t):
    return unicode(t.decode('cp1252'))

class Formatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter): pass

def make_parser():

    description=[
        "Recursively stat files\n",
        "Modes:\n"
    ]

    for mode in MODES:
        description.append("% 12s: %s" % (
            mode.__name__, mode.__doc__.split('\n', 1)[0]))

    parser = argparse.ArgumentParser(
        description='\n'.join(description),
        formatter_class=Formatter
    )

    modenames = [i.__name__ for i in MODES]
    def mode_check(x):
        if x not in modenames:
            raise argparse.ArgumentTypeError(
                "%s not in %s" % (x, modenames))
        return x

    group = parser.add_argument_group('required arguments')
    group.add_argument("--mode", default=MODES[0].__name__,
        help="mode from list above", type=mode_check
    )

    parser.add_argument("--top-dir", default='.',
        help="path to start from", metavar='DIR'
    )
    parser.add_argument("--show-n", type=int, default=0,
        help="show this many results in summaries, 0 == all",
        metavar='N'
    )
    parser.add_argument("--extensions", nargs='+',
        help="extensions to list in find_ext mode",
        metavar='EXT', default=['jpg', 'dat', 'txt']
    )
    parser.add_argument("--min-size", metavar='BYTES', type=int,
        help="ignore files smaller than this size")
    parser.add_argument("--max-size", metavar='BYTES', type=int,
        help="ignore files larger than this size")
    parser.add_argument("--path-filter", metavar="REGEX",
        help="regular expression paths must match, case insensitive")
    parser.add_argument("--file-filter", metavar="REGEX",
        help="regular expression files must match, case insensitive. "
            "Use '^(?!.*<pattern>)' to exclude <pattern>, e.g. "
            '--file-filter "^(?!.*(jpg|dat))"')
    parser.add_argument("--dupes-sort-n", default=False,
        action="store_true",
        help="sort dupe listing by count, not size")
    parser.add_argument("--dupes-hash", default=False,
        action="store_true",
        help="hash possible dupes to check content, don't just use size")

    return parser
def get_data(opt):
    """get_data - generator, read data, applying filters

    :param argparse.Namespace opt: command line options
    """

    filtered = any([opt.file_filter, opt.max_size, opt.min_size])

    for line in sys.stdin:
        data = json.loads(line)
        if (opt.path_filter and
            not opt.path_filter.search(data['path'])):
            continue
        # print data['files'][0][7], data['files'][0][7] <= opt.max_size
        data['files'] = [
            i for i in data['files']
            if (opt.max_size is None or i[7] <= opt.max_size)
               and
               (opt.min_size is None or i[7] >= opt.min_size)
               and
               (opt.file_filter is None or opt.file_filter.search(i[0]))
        ]
        if data['files'] or not filtered:
            yield data
def get_hash(path):
    """get_hash - get hash for file

    :param str path: path to file
    :return: sha1 hash of file
    :rtype: str
    """

    buff_size = 10000000
    import hashlib
    digest = hashlib.sha1()
    infile = open(path, 'rb')
    while True:
        data = infile.read(buff_size)
        digest.update(data)
        if len(data) != buff_size:
            break
    return digest.hexdigest()
@mode
def recur_stat(opt):
    "Recursively stat folder"
    count = 0
    for path, dirs, files in os.walk(opt.top_dir):
        out = {'path':uni(path), 'files':[]}
        for filename in files:
            count += 1
            out['files'].append(tuple([uni(filename)]) +
                tuple(os.stat(os.path.join(path, filename))))
        print json.dumps(out)
        sys.stderr.write("%d %s\n" % (count, path))

@mode
def find_ext(opt):
    "Find folders with files with listed extensions"
    exts = defaultdict(lambda: defaultdict(lambda: 0))

    for data in get_data(opt):

        for fileinfo in data['files']:
            name, ext = os.path.splitext(fileinfo[0])
            exts[ext.upper()][data['path']] += 1

    pathcount = defaultdict(lambda: defaultdict(lambda: 0))

    for ext in opt.extensions:
        for path in exts['.'+ext]:
            pathcount[path][ext] = exts['.'+ext][path]

    writer = csv.writer(sys.stdout)
    writer.writerow(opt.extensions+['path'])
    order = sorted(
        pathcount,
        key=lambda path: sum(pathcount[path].values()),
        reverse=True
    )
    for n, path in enumerate(order):
        row = [str(pathcount[path][i]) for i in opt.extensions]+[path]
        writer.writerow(row)
        if opt.show_n and n+1 >= opt.show_n:
            break
@mode
def rank_ext(opt):
    "Rank extensions by popularity"

    exts = defaultdict(lambda: defaultdict(lambda: 0))

    for data in get_data(opt):

        for fileinfo in data['files']:
            name, ext = os.path.splitext(fileinfo[0])
            exts[ext.upper()][data['path']] += 1
            exts[ext.upper()]['__COUNT'] += 1

    counts = [[exts[i]['__COUNT'], i] for i in exts]
    counts.sort(reverse=True)
    for i in counts[:opt.show_n] if opt.show_n else counts:
        print "% 5d %s" % tuple(i)
@mode
def summary(opt):
    "Summary of files in data"

    dirs = files = bytes = 0

    for data in get_data(opt):

        dirs += 1

        for fileinfo in data['files']:
            files += 1
            bytes += fileinfo[7]

    print "{dirs:,d} folders, {files:,d} files, {bytes:,d} bytes".format(
        dirs=dirs, files=files, bytes=bytes)
@mode
def dirs(opt):
    """Dumps dirs

    :param argparse.Namespace opt: command line options
    """

    for n, data in enumerate(get_data(opt)):
        print data['path']
        if opt.show_n and n+1 >= opt.show_n:
            break
@mode
def files(opt):
    """Dumps files

    :param argparse.Namespace opt: command line options
    """

    count = 0
    for data in get_data(opt):
        for fileinfo in data['files']:
            print os.path.join(data['path'], fileinfo[0])
            count += 1
            if opt.show_n and count == opt.show_n:
                return
@mode
def dupes(opt):
    "Find duplicate files"

    # group by size
    sizes = defaultdict(lambda: [])
    for data in get_data(opt):
        for filedata in data['files']:
            fileinfo = FileInfo(*filedata)
            sizes[fileinfo.st_size].append((data['path'], fileinfo.name))

    # sort by size or count
    if opt.dupes_sort_n:
        order = sorted(sizes, reverse=True,
            key=lambda x:len(sizes[x]))
    else:
        order = sorted(sizes, reverse=True)

    n = 0
    for size in order:
        if len(sizes[size]) < 2:
            continue

        # within sizes with multiples, hash files, maybe
        hashed = defaultdict(lambda: [])
        for path, filename in sizes[size]:
            filepath = os.path.join(path, filename)
            if opt.dupes_hash:
                hashtext = get_hash(filepath)
            else:
                hashtext = 'no-hash'
            hashed[(size, hashtext)].append(filepath)

        # filter out singles
        hashed = {k:v for k,v in hashed.items() if len(v) > 1}

        for sizehash in hashed:
            if len(hashed) > 1:  # same size, multiple contents
                sizetext = "%s:%s" % sizehash
            else:  # same content for all
                sizetext = sizehash[0]
            print sizetext, len(hashed[sizehash]), hashed[sizehash]
            n += 1

        # might overshoot, but better to show complete sets of dupes
        if opt.show_n and n+1 >= opt.show_n:
            break
def main():
    """main - tweak options are dispatch mode
    """

    opt = make_parser().parse_args()
    opt.extensions = [i.upper() for i in opt.extensions]
    for attr in 'file', 'path':
        regex = getattr(opt, attr+'_filter')
        if regex:
            setattr(opt, attr+'_filter',
                re.compile(regex, flags=re.IGNORECASE))

    globals()[opt.mode](opt)
if __name__ == '__main__':
    main()
