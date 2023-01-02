import random
import shutil
from pathlib import Path
from random import choices, randint

MAXDEPTH = 4
FILES = (3, 8)
DUPE_PCT = 10
DUPE_DIRS = 3
DIRS = (DUPE_DIRS, DUPE_DIRS + 3)
SIZE = (0, 1000)
# use these for unusual characters in file names to test assumptions
CHARS = "".join(chr(i) for i in range(ord(" "), ord("z") + 1)) + "€ह𐍈¢☐☑☒"
# or these for simpler file names
CHARS = "".join(chr(i) for i in range(ord("a"), ord("z") + 1))
CHARS = CHARS.replace("\\", "").replace("/", "")
NAMELEN = (1, 20)
SEED = "RANDOMFILESYSTEM60923583"


def makefilehier(base, seed=None, _depth=0, _dirs=None, _files=None):
    """Create a random file hierarchy

    Args:
        base (str): path at which to create files
        seed (str/False): something to be used by random.seed(), use False
                          to not use any seed, omit to use preset default.
    """
    if seed is None:
        seed = SEED
    if seed is not False:
        random.seed(seed)
    base = Path(base)
    base.mkdir(exist_ok=True)
    if _depth == 0:
        _dirs = []  # list of dirs created
        _files = []  # list of files created
    todo = randint(*FILES)
    file_i = 0
    while file_i < todo:
        name = "".join(choices(CHARS, k=randint(*NAMELEN)))
        filepath = base / name
        if filepath.exists():
            continue
        file_i += 1
        size = randint(*SIZE)
        data = "".join(choices(CHARS, k=size)).encode("utf-8")
        _files.append(filepath)
        filepath.write_bytes(data)

    todo = randint(*DIRS)
    dir_i = 0
    while dir_i < todo:
        name = "".join(choices(CHARS, k=randint(*NAMELEN)))
        dirpath = base / name
        if dirpath.exists():
            continue
        dir_i += 1
        _dirs.append(dirpath)
        dirpath.mkdir(exist_ok=True)
        if _depth < MAXDEPTH:
            makefilehier(
                base=dirpath, seed=False, _depth=_depth + 1, _dirs=_dirs, _files=_files
            )

    if _depth == 0:
        for filepath in _files:  # duplicate DUPE_PCT of files to random folders
            if randint(0, 99) < DUPE_PCT:
                dirpath = random.choice(_dirs)
                (dirpath / (filepath.name + "2")).write_bytes(filepath.read_bytes())

        dupe_dirs(_dirs)


def dupe_dirs(_dirs):
    """Duplicate dirs various numbers of times."""

    # use only dirs that contain files *in the dir and in a subdir*
    dir_dupes = [
        i
        for i in _dirs
        if any(j.is_file() for j in i.glob("*"))
        and any(j.is_file() and j.parent != i for j in i.glob("**/*"))
    ]
    random.shuffle(dir_dupes)
    use_dupes = []
    # Pick non-overlapping dirs
    while len(use_dupes) < DUPE_DIRS:
        candidate = dir_dupes.pop(0)
        base = candidate.parts[1]  # .parts[0] is 'testfs'
        print(base)
        if not any(i.parts[1] == base for i in use_dupes):
            use_dupes.append(candidate)

    for dupe_n in range(DUPE_DIRS):
        src = dir_dupes[dupe_n]
        for dupe_i in range(1, dupe_n + 1 + 1):
            dst = f"{src}_dupe{dupe_i}"
            shutil.copytree(src, dst)
        if dupe_n == 0:  # Make this a false dupe
            # Find a file at least 8 bytes long, overwrite first 8 bytes with 'FAKEDUPE'
            file = next(
                i
                for i in Path(dst).glob("**/*")
                if i.is_file() and i.stat().st_size >= 8
            )
            with file.open("r+") as out:
                out.write("FAKEDUPE")


if __name__ == "__main__":
    makefilehier("testfs")
