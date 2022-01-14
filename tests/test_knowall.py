"""
knowall tests - NOTE: test_default *must* run first (which, by default, it does).
"""
import shutil
import sys
from io import StringIO
from pathlib import Path

import pytest
from dateutil.parser import ParserError

import knowall
from tests.mkfakefs import makefilehier

TEST_DATA = "test.jsonl"
TEST_DB = "pytest_test.db"
TOP_DIR = ["--top-dir", "testfs"]


@pytest.fixture(scope="session")
def top_dir():
    """Create test file system (folder) and return path."""
    tempfs = TOP_DIR[1]
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
    out = _out.getvalue()

    sys.stdin = old_in
    sys.stdout = old_out
    _out.close()

    return out


# This test MUST RUN FIRST
def test_default(top_dir):
    """Test creation of output file"""
    out = run_args(path_in=None)
    assert (
        '{"path": "testfs/gjuziyvlz/eoebtos/acvvqpvhuqkllvwlhs/v/judgkpoddlhw", '
        '"files": []}' in out
    )
    with Path(TEST_DATA).open("w") as test_data:
        test_data.write(out)


def test_dupes():
    out = run_args(["--mode", "dupes"])
    assert "files: 8" in out


def test_dupes_w_db():
    if Path(TEST_DB).exists():
        Path(TEST_DB).unlink()
    out = run_args(["--mode", "dupes", "--hash-db", TEST_DB])
    assert Path(TEST_DB).exists()
    print(out)

    # def test_dupes_w_db_no_hash():
    #     # FIXME: make test test something
    #     sys.argv[1:] = TOP_DIR + [
    #         "--mode",
    #         "dupes",
    #         "--hash-db",
    #         "test.db",
    #         "--dupes-no-hash",
    #         "--dupes-sort-n",
    #         "--show-n",
    #         "3",
    #     ]
    #     os.chdir(os.path.dirname(__file__))
    #     sys.stdin = open(TEST_DATA)
    #     knowall.main()

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

    # def test_dirs():
    #     # FIXME: make test test something
    #     sys.argv[1:] = TOP_DIR + ["--mode", "dirs", "--show-n", "3"]
    #     os.chdir(os.path.dirname(__file__))
    #     sys.stdin = open(TEST_DATA)
    #     knowall.main()

    # def test_summary():
    #     # FIXME: make test test something
    #     sys.argv[1:] = TOP_DIR + ["--mode", "summary"]
    #     os.chdir(os.path.dirname(__file__))
    #     sys.stdin = open(TEST_DATA)
    #     knowall.main()

    # def test_find_ext():
    #     # FIXME: make test test something
    #     sys.argv[1:] = TOP_DIR + ["--mode", "find_ext"]
    #     os.chdir(os.path.dirname(__file__))
    #     sys.stdin = open(TEST_DATA)
    #     knowall.main()

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

    # def test_nonexistentmode():
    #     # FIXME: make test test something
    #     sys.argv[1:] = TOP_DIR + ["--mode", "nonexistentmode"]
    #     os.chdir(os.path.dirname(__file__))
    #     sys.stdin = open(TEST_DATA)
    #     with pytest.raises(SystemExit):
    #         knowall.main()

    # def test_resume_from():
    #     # FIXME: make test test something
    #     sys.argv[1:] = TOP_DIR + [
    #         "--resume-from",
    #         f"testfs{os.sep}mw{os.sep}gzgnowizklqny",
    #     ]
    #     os.chdir(os.path.dirname(__file__))
    #     sys.stdin = open(TEST_DATA)
    #     knowall.main()
