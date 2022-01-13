import random
from pathlib import Path
from random import choices, randint

MAXDEPTH = 4
FILES = (3, 8)
DUPE_PCT = 10
DIRS = (0, 3)
SIZE = (0, 100000)
# use these for unusual characters in file names to test assumptions
CHARS = "".join(chr(i) for i in range(ord(" "), ord("z") + 1)) + "€ह𐍈¢☐☑☒"
# or these for simpler file names
CHARS = "".join(chr(i) for i in range(ord("a"), ord("z") + 1))
CHARS = CHARS.replace("\\", "").replace("/", "")
NAMELEN = (1, 20)
SEED = "RANDOMFILESYSTEM60923584"


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
    for file_i in range(0, randint(*FILES)):
        name = "".join(choices(CHARS, k=randint(*NAMELEN)))
        size = randint(*SIZE)
        data = "".join(choices(CHARS, k=size)).encode("utf-8")
        filepath = base / name
        _files.append(filepath)
        filepath.write_bytes(data)

    for dir_i in range(0, randint(*DIRS)):
        name = "".join(choices(CHARS, k=randint(*NAMELEN)))
        dirpath = base / name
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


if __name__ == "__main__":
    makefilehier("testfs")
