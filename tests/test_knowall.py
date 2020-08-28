import argparse
import os
import sys

import pytest
from dateutil.parser import ParserError

import knowall

TOP_DIR = ['--top-dir', 'testfs']


def test_default():
    # FIXME: make test test something
    sys.argv[1:] = TOP_DIR
    os.chdir(os.path.dirname(__file__))
    sys.stdout = open("test.jsonl", 'w')
    knowall.main()


def test_dupes():
    # FIXME: make test test something
    sys.argv[1:] = TOP_DIR + ['--mode', 'dupes']
    os.chdir(os.path.dirname(__file__))
    sys.stdin = open("test.jsonl")
    knowall.main()


def test_dupes_w_db():
    # FIXME: make test test something
    sys.argv[1:] = TOP_DIR + ['--mode', 'dupes', '--hash-db', 'test.db']
    os.chdir(os.path.dirname(__file__))
    if os.path.exists('test.db'):
        os.unlink('test.db')
    sys.stdin = open("test.jsonl")
    knowall.main()


def test_dupes_w_db_no_hash():
    # FIXME: make test test something
    sys.argv[1:] = TOP_DIR + [
        '--mode',
        'dupes',
        '--hash-db',
        'test.db',
        '--dupes-no-hash',
        '--dupes-sort-n',
        '--show-n', '3',
    ]
    os.chdir(os.path.dirname(__file__))
    sys.stdin = open("test.jsonl")
    knowall.main()


def test_files():
    # FIXME: make test test something
    sys.argv[1:] = TOP_DIR + [
        '--mode',
        'files',
        '--show-time',
        'M',
        '--show-n',
        '3',
    ]
    os.chdir(os.path.dirname(__file__))
    sys.stdin = open("test.jsonl")
    knowall.main()


def test_dirs():
    # FIXME: make test test something
    sys.argv[1:] = TOP_DIR + ['--mode', 'dirs', '--show-n', '3']
    os.chdir(os.path.dirname(__file__))
    sys.stdin = open("test.jsonl")
    knowall.main()


def test_variants():
    # FIXME: make test test something
    sys.argv[1:] = TOP_DIR + ['--mode', 'variants']
    os.chdir(os.path.dirname(__file__))
    sys.stdin = open("test.jsonl")
    knowall.main()


def test_summary():
    # FIXME: make test test something
    sys.argv[1:] = TOP_DIR + ['--mode', 'summary']
    os.chdir(os.path.dirname(__file__))
    sys.stdin = open("test.jsonl")
    knowall.main()


def test_find_ext():
    # FIXME: make test test something
    sys.argv[1:] = TOP_DIR + ['--mode', 'find_ext']
    os.chdir(os.path.dirname(__file__))
    sys.stdin = open("test.jsonl")
    knowall.main()


def test_rank_ext():
    # FIXME: make test test something
    sys.argv[1:] = TOP_DIR + ['--mode', 'rank_ext']
    os.chdir(os.path.dirname(__file__))
    sys.stdin = open("test.jsonl")
    knowall.main()


def test_variants():
    # FIXME: make test test something
    sys.argv[1:] = TOP_DIR + ['--mode', 'variants']
    os.chdir(os.path.dirname(__file__))
    sys.stdin = open("test.jsonl")
    knowall.main()


def test_dupe_dirs():
    # FIXME: make test test something
    sys.argv[1:] = TOP_DIR + ['--mode', 'dupe_dirs']
    os.chdir(os.path.dirname(__file__))
    sys.stdin = open("test.jsonl")
    with pytest.raises(TypeError):
        knowall.main()


def test_filters():
    # FIXME: make test test something
    sys.argv[1:] = TOP_DIR + [
        '--mode',
        'summary',
        '--path-filter',
        'x',
        '--file-filter',
        'x',
        '--min-mtime',
        '1979/1/1',
    ]
    os.chdir(os.path.dirname(__file__))
    sys.stdin = open("test.jsonl")
    knowall.main()


def test_filters_no_files():
    # FIXME: make test test something
    sys.argv[1:] = TOP_DIR + [
        '--mode',
        'summary',
        '--file-filter',
        'nofilesmatchthis',
    ]
    os.chdir(os.path.dirname(__file__))
    sys.stdin = open("test.jsonl")
    knowall.main()


def test_filters_bad_date():
    # FIXME: make test test something
    sys.argv[1:] = TOP_DIR + [
        '--mode',
        'summary',
        '--file-filter',
        'x',
        '--min-mtime',
        '19799/1/1',
    ]
    os.chdir(os.path.dirname(__file__))
    sys.stdin = open("test.jsonl")
    with pytest.raises(ParserError):
        knowall.main()


def test_nonexistentmode():
    # FIXME: make test test something
    sys.argv[1:] = TOP_DIR + ['--mode', 'nonexistentmode']
    os.chdir(os.path.dirname(__file__))
    sys.stdin = open("test.jsonl")
    with pytest.raises(SystemExit):
        knowall.main()


def test_resume_from():
    # FIXME: make test test something
    sys.argv[1:] = TOP_DIR + [
        '--resume-from',
        f'testfs{os.sep}mw{os.sep}gzgnowizklqny',
    ]
    os.chdir(os.path.dirname(__file__))
    sys.stdin = open("test.jsonl")
    knowall.main()
