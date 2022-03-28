# knowall.py

Recursively stat's a directory hierarchy, dumping data to a file.
Then analyses that data in different ways.

```
usage: knowall.py [-h] [--mode MODE] [--top-dir DIR] [--show-n N]
                  [--extensions EXT [EXT ...]] [--min-size BYTES]
                  [--max-size BYTES] [--path-filter REGEX]
                  [--file-filter REGEX] [--ignore-hidden BOOL]
                  [--out-file FILE] [--min-ctime TIME] [--max-ctime TIME]
                  [--min-mtime TIME] [--max-mtime TIME] [--min-atime TIME]
                  [--max-atime TIME] [--show-time TIMES] [--dupes-sort-n]
                  [--dupes-no-hash] [--hash-db HASH_DB] [--resume-from PATH]
                  [--sort TYPE] [--reverse]

Recursively stat files. e.g.

    # first collect data
    python knowall.py --top-dir some/path > some_path.json
    # then analyze - 5 largest dupes.
    python < some_path.json --mode dupes --show-n 5
    # most common extensions on subpath
    python < some_path.json --mode rank_ext --path-filter some/path/here

Modes:

  recur_stat: Recursively stat folder, store this output for other modes
  find_ext: Find folders with files with listed extensions
  rank_ext: Rank extensions by popularity
  summary: Summary of files in data
  dirs: Dumps dirs
  files: Dumps files
  dupes: Find duplicate files
  dupe_dirs: Find duplicate dirs., list from largest to smallest
  folderstats_pkg: Use folderstats package to recursively stat a directory (faster than recur_stat and handles Windows filepath limits)

optional arguments:
  -h, --help            show this help message and exit
  --top-dir DIR         path to start from (default: .)
  --show-n N            show this many results in summaries, 0 == all
                        (default: 0)
  --extensions EXT [EXT ...]
                        extensions to list in find_ext mode (default: ['jpg',
                        'dat', 'txt'])
  --min-size BYTES      ignore files smaller than this size (default: None)
  --max-size BYTES      ignore files larger than this size (default: None)
  --path-filter REGEX   regular expression paths must match, case insensitive
                        (default: None)
  --file-filter REGEX   regular expression files must match, case insensitive.
                        Use '^(?!.*<pattern>)' to exclude <pattern>, e.g.
                        --file-filter "^(?!.*(jpg|dat))" (default: None)
  --ignore-hidden BOOL  folderstats mode to ignore hidden files or not
                        (default: True)
  --out-file FILE       folderstats mode filename or path to save output to
                        CSV (default: folderstats_mode_output.csv)
  --min-ctime TIME      Minimum creation time (default: None)
  --max-ctime TIME      Maximum creation time, free format, e.g. YYYYMMDDHHMM
                        (default: None)
  --min-mtime TIME      Minimum modification time (default: None)
  --max-mtime TIME      Maximum modification time, free format, e.g.
                        YYYYMMDDHHMM (default: None)
  --min-atime TIME      Minimum access time (default: None)
  --max-atime TIME      Maximum access time, free format, e.g. YYYYMMDDHHMM
                        (default: None)
  --show-time TIMES     Any combination of 'C', 'M', 'A', e.g. MA, times to
                        show in file mode (default: None)
  --dupes-sort-n        sort dupe listing by count, not size (default: False)
  --dupes-no-hash       don't hash possible dupes to check content, just use
                        size. WARNING: may return false dupe listings.NOTE:
                        does not calc. *new* hashes, will still use hashes
                        from --hash-db (default: False)
  --hash-db HASH_DB     SQLite DB of hash values to check/update before/when
                        hashing (default: None)
  --resume-from PATH    skip paths before (alphabetically) PATH to resume
                        interrupted indexing (default: None)
  --sort TYPE           Type of sorting, from list above. (default: None)
  --reverse             Reverse sorting. (default: False)

required arguments:
  --mode MODE           mode from list above (default: recur_stat)
```

## Dev. notes

Run tests/mkfakefs.py in tests to create testfs/ there.

Run tests and generate coverage report

    coverage run -m pytest && coverage report && coverage html
    
