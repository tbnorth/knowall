"""
knowall tests - NOTE: test_default *must* run first (which, by default, it does).
"""
import os
import shutil
import sqlite3
import sys
from io import StringIO
from pathlib import Path

import pytest

import knowall
from tests.mkfakefs import makefilehier

# from dateutil.parser import ParserError


TEST_DATA = "test.jsonl"
TEST_DB = "pytest_test.db"
TOP_DIR = ["--top-dir", "testfs"]


def query_hash_db(query):
    con = sqlite3.connect(TEST_DB)
    data = list(con.execute(query))
    con.close()
    return data


@pytest.fixture(scope="session")
def top_dir():
    """Create test file system (folder) and return path."""
    tempfs = TOP_DIR[1]
    if Path(tempfs).exists():
        shutil.rmtree(tempfs)
    makefilehier(tempfs)
    return tempfs


def run_args(args=None, path_in=TEST_DATA):
    """Run with args"""
    sys.argv[1:] = TOP_DIR + (args or [])
    old_in = sys.stdin
    old_out = sys.stdout
    if path_in is not None:
        sys.stdin = open(path_in)
    _out = StringIO()
    sys.stdout = _out
    knowall.main()
    # To avoid sqlite3.OperationalError: attempt to write a readonly database:
    knowall.hash_db_con_cur.cache_clear()
    out = _out.getvalue()

    sys.stdin = old_in
    sys.stdout = old_out
    _out.close()

    return out


def os_path(path: str) -> str:
    # JSON encoding of Window's '\' is '\\\\', so string based comparisons are tricky
    if os.sep == "\\":
        return path.replace("/", "\\\\")
    return path


# This test MUST RUN FIRST
def test_default(top_dir):
    """Test creation of output file"""
    print(top_dir)
    out = run_args(path_in=None)
    path = os_path("testfs/u/t/pdwjhvffkchm/xoogtbhppacj/pbinlyqritejwnlvzmgp")
    print(path)
    assert f'{{"path": "{path}", ' '"files": []}' in out
    with Path(TEST_DATA).open("w") as test_data:
        test_data.write(out)


def test_dupes():
    Path(TEST_DB).unlink(missing_ok=True)
    out = run_args(["--mode", "dupes"])
    assert not Path(TEST_DB).exists()
    assert "files: 330" in out


def test_dupes_w_db_no_hash():
    Path(TEST_DB).unlink(missing_ok=True)
    out = run_args(
        [
            "--mode",
            "dupes",
            "--hash-db",
            TEST_DB,
            "--dupes-no-hash",
            "--dupes-sort-n",
            "--show-n",
            "3",
        ]
    )
    assert Path(TEST_DB).exists()
    assert (len(list(query_hash_db("select * from hash")))) == 0
    print(out)


def test_dupes_w_db():
    Path(TEST_DB).unlink(missing_ok=True)
    out = run_args(["--mode", "dupes", "--hash-db", TEST_DB])
    assert Path(TEST_DB).exists()
    print(list(Path().glob("*")))
    assert "files: 330" in out
    assert (len(list(query_hash_db("select * from hash")))) == 3038


def hier_test(_):
    return [
        {"path": "/a", "files": ["x", "y"]},
        {"path": "/a/b", "files": ["x", "z"]},
        {"path": "/a/b/c", "files": ["z", "y"]},
    ]


def test_get_hier_db(mocker):
    mocker.patch("knowall.get_data", new=hier_test)
    hier = knowall.get_hier_db(None)
    print(hier)
    assert len(hier) == 2  # FILES + 'a'
    assert len(hier["a"]) == 2  # FILES + 'b'
    assert len(hier["a"]["b"]) == 2  # FILES + 'c'
    assert len(hier["a"]["b"]["c"]) == 1  # FILES
    assert hier["a"]["b"]["c"][knowall.FILES] == ["z", "y"]
    assert hier["a"][knowall.FILES] == ["x", "y"]

    # def test_files():
    #     # FIXME: make test test something
    #     sys.argv[1:] = TOP_DIR + [
    #         "--mode",
    #         "files",
    #         "--show-time",
    #         "M",
    #         "--show-n",
    #         "3",
    #     ]
    #     os.chdir(os.path.dirname(__file__))
    #     sys.stdin = open(TEST_DATA)
    #     knowall.main()


def test_files():
    # Cannot test --show-time because testfs is modified every pytest run, so times
    # change
    out = run_args(["--mode", "files", "--show-n", "3"])
    out = [os_path(x) for x in out.split("\n") if x]
    # Check show-n matched 3
    assert (len(out)) == 3
    # Check files listed are correct
    # file ordering varies by OS, so exactly 3 of these should match
    all_files = set(i for i in Path("testfs").glob("**/*") if i.is_file())
    three_files = set(Path(i) for i in out)
    assert len(all_files & three_files) == 3


def test_dirs():
    # FIXME: make test test something
    out = run_args(["--mode", "dirs", "--show-n", "3"])
    out = [os_path(x) for x in out.split("\n") if x]
    # Check show-n matched 3
    assert (len(out)) == 3
    # Check files listed are correct
    # file ordering varies by OS, so exactly 3 of these should match
    all_dirs = set(Path("testfs").glob("**"))
    three_dirs = set(Path(i) for i in out)
    assert len(all_dirs & three_dirs) == 3


def test_summary():
    # FIXME: make test test something
    out = run_args(["--mode", "summary"])
    assert out == "2,435 folders, 3,184 files, 1,589,966 bytes, no stats. 0\n"

    # def test_find_ext():
    #     # FIXME: make test test something
    #     # Need to add test files with extensions first...
    #     out = run_args(["--mode", "find_ext"])

    # def test_rank_ext():
    #     # FIXME: make test test something
    #     sys.argv[1:] = TOP_DIR + ["--mode", "rank_ext"]
    #     os.chdir(os.path.dirname(__file__))
    #     sys.stdin = open(TEST_DATA)
    #     knowall.main()

    # def test_variants():
    #     # FIXME: make test test something
    #     sys.argv[1:] = TOP_DIR + ["--mode", "variants"]
    #     os.chdir(os.path.dirname(__file__))
    #     sys.stdin = open(TEST_DATA)
    #     knowall.main()

    # def test_dupe_dirs():
    #     # FIXME: make test test something
    #     sys.argv[1:] = TOP_DIR + ["--mode", "dupe_dirs"]
    #     os.chdir(os.path.dirname(__file__))
    #     sys.stdin = open(TEST_DATA)
    #     knowall.main()

    # def test_filters():
    #     # FIXME: make test test something
    #     sys.argv[1:] = TOP_DIR + [
    #         "--mode",
    #         "summary",
    #         "--path-filter",
    #         "x",
    #         "--file-filter",
    #         "x",
    #         "--min-mtime",
    #         "1979/1/1",
    #     ]
    #     os.chdir(os.path.dirname(__file__))
    #     sys.stdin = open(TEST_DATA)
    #     knowall.main()

    # def test_filters_no_files():
    #     # FIXME: make test test something
    #     sys.argv[1:] = TOP_DIR + [
    #         "--mode",
    #         "summary",
    #         "--file-filter",
    #         "nofilesmatchthis",
    #     ]
    #     os.chdir(os.path.dirname(__file__))
    #     sys.stdin = open(TEST_DATA)
    #     knowall.main()

    # def test_filters_bad_date():
    #     # FIXME: make test test something
    #     sys.argv[1:] = TOP_DIR + [
    #         "--mode",
    #         "summary",
    #         "--file-filter",
    #         "x",
    #         "--min-mtime",
    #         "19799/1/1",
    #     ]
    #     os.chdir(os.path.dirname(__file__))
    #     sys.stdin = open(TEST_DATA)
    #     with pytest.raises(ParserError):
    #         knowall.main()


def test_nonexistentmode(capsys):
    # https://stackoverflow.com/questions/30256332/verify-the-error-code-or-message-from-systemexit-in-pytest
    # Have to run with python -m pytest --capture=sys for it to work
    with pytest.raises(SystemExit):
        run_args(["--mode", "nonexistentmode"])
    out, err = capsys.readouterr()
    assert "error: argument --mode: nonexistentmode not in" in err

    # def test_resume_from():
    #     # FIXME: make test test something
    #     sys.argv[1:] = TOP_DIR + [
    #         "--resume-from",
    #         f"testfs{os.sep}mw{os.sep}gzgnowizklqny",
    #     ]
    #     os.chdir(os.path.dirname(__file__))
    #     sys.stdin = open(TEST_DATA)
    #     knowall.main()
