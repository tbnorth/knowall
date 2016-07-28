# knowall.py

Recursively stat's a directory hierarchy, dumping data to a file.
Then analyses that data in different ways.

```
# first collect data
python knowall.py --top-dir some/path > some_path.json

# then analyze

# 5 largest dupes.
python < some_path.json --mode dupes --show-n 5 

# most common extensions on subpath
python < some_path.json --mode rank_ext --path-filter some/path/here


usage: knowall.py [-h] [--mode MODE] [--top-dir DIR] [--show-n N]
                  [--extensions EXT [EXT ...]] [--min-size BYTES]
                  [--max-size BYTES] [--path-filter REGEX]
                  [--file-filter REGEX] [--dupes-sort-n] [--dupes-hash]

Recursively stat files

Modes:

  recur_stat: Recursively stat folder
    find_ext: Find folders with files with listed extensions
    rank_ext: Rank extensions by popularity
     summary: Summary of files in data
        dirs: Dumps dirs
       files: Dumps files
       dupes: Find duplicate files

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
  --dupes-sort-n        sort dupe listing by count, not size (default: False)
  --dupes-hash          hash possible dupes to check content, don't just use
                        size (default: False)

required arguments:
  --mode MODE           mode from list above (default: recur_stat)
```
