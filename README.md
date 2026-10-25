# schools-tool

Counts and plain-text search over the NCES Common Core of Data public school file for 2005-06 (states A–I, 34,779 schools). It answers the [programming challenge](docs/challenge.md): Part 1 counts schools by state, locale and city; Part 2 finds a school from a free-text query in a few milliseconds.

## Quick start

```bash
uv sync
uv run schools-tool counts                      # Part 1 report
uv run schools-tool counts --output-dir output  # also write the counts as CSV files
uv run schools-tool search foley high alabama   # Part 2: top 3 matches
uv run schools-tool search                      # one query per line from stdin
```

The functions the challenge asks for work as described there:

```python
>>> from schools_tool import count_schools, school_search
>>> count_schools.print_counts()
>>> results = school_search.search_schools("elementary school highland park")
Results for "elementary school highland park" (search took: 0.004s)
1. HIGHLAND PARK ELEMENTARY SCHOOL
PUEBLO, CO
2. HIGHLAND PARK ELEMENTARY SCHOOL
MUSCLE SHOALS, AL
3. HIGHLAND PARK ELEM SCH
BLOOMINGTON, IN
```

`search_schools` prints the results and also returns them as `School` records. To use another CSV in the same NCES layout, put `--data PATH` before the command (`schools-tool --data PATH counts`), or pass the path to `load_schools`.

## Part 1 answers

| Question | Answer |
| --- | --- |
| Total schools | 34,779 |
| Schools per state | 20 states; CA has the most (9,969). Full list from `schools-tool counts` |
| Schools per metro-centric locale | 1: 4,862, 2: 5,383, 3: 8,180, 4: 3,829, 5: 270, 6: 2,592, 7: 4,276, 8: 4,291, N (no locale assigned): 1,096 |
| City with the most schools | CHICAGO, IL (657) |
| Unique cities with at least one school | 5,684 |

A city is a city name plus its state, so SPRINGFIELD, IL and SPRINGFIELD, CO count as two cities. Counting by name alone would give 4,787 cities. One spelling counts per city: FT. LAUDERDALE, FT LAUDERDALE and FORT LAUDERDALE are one city (see [Data](#data)). One school has no city in the file and isn't counted toward cities. If several cities tie for the most schools, the report lists all of them.

The dataset covers states A–I, but MD, NV, OH and OR each have one school. Each is run by a district in an A–I state, and the count uses the state the school is located in.

## How search ranks results

`SchoolIndex` builds an inverted index of the words in each school's name, city and state, once and up front (about 0.25 s). A search then looks at only the schools that share a word with the query. The rules, which are also in the [`school_search`](src/schools_tool/school_search.py) docstring:

1. **Matching.** A query word matches a word in the school's name, city or state name. Matching ignores case and punctuation, including apostrophes such as the backtick in RIVER\`S EDGE, and leading zeros ("044" finds 44). An exact match scores 10 points, and so does a common abbreviation: "elementary" finds ELEM, which 2,229 names use, and "saint" finds ST. A word that starts a longer word scores 6 ("highl" finds HIGHLAND). A word that matches nothing else may match a word one typo away for 5 ("kuskokwin" finds KUSKOKWIM).
2. **State codes and connecting words.** A postal code counts only as the last word, where it means only the state: "lamar co" is Lamar, Colorado, not LAMAR COUNTY. Connecting words such as "in", "of" and "the" are skipped. Without these two rules, "high school in chicago" returned junior highs in East Chicago, Indiana.
3. **Rarity.** Points are multiplied by roughly log2 of how rare the word is. In "foley high alabama", FOLEY (5 schools) decides much more than HIGH (6,467), and SCHOOL (in 57% of names) barely counts.
4. **Ties.** Among equal scores, the tie-breakers are applied in this order:
   1. Fewest name words the query doesn't match. That puts HIGHLAND PARK ELEMENTARY SCHOOL above elementary schools located in Highland Park, IL; CALIFORNIA HIGH in San Ramon above SAN RAMON VALLEY HIGH in Danville; THE ACADEMY in San Jose above SAN JOSE HIGH ACADEMY; and KENNESAW ELEM SCHOOL above other elementary schools in Kennesaw.
   2. More query word pairs side by side, in order, in the name or city. "illinois school park forest" finds the school in PARK FOREST, not FOREST PARK, and "rancho cucamonga middle" finds RANCHO CUCAMONGA MIDDLE before CUCAMONGA MIDDLE.
   3. The spelling as typed over an abbreviation (ELEMENTARY over ELEM).
   4. More query words in the name.
   5. The city that best matches the query.
   6. Shorter names.
   7. Alphabetical order, so results never depend on file order.
5. **Duplicates.** Results with the same name, city and state are shown once. The file has 118 such groups, mostly a school listed under an old and a new district.

All six README test cases return the expected top hits (`tests/test_school_search.py::TestReadmeCases`). For a broader check, searching each school by its own name, city and state finds it among the top three results. The test samples 300 schools per run. Across all 34,779 schools, 34,770 rank first and every school is in the top three. The other nine are pairs whose queries come down to the same words. Four differ only in punctuation (ST. DAVID and ST DAVID). Five differ only by a skipped connecting word ("ARTS AND SCIENCES" and "ARTS/SCIENCES"), or by whether a word is in the name or the city (CUCAMONGA MIDDLE and RANCHO CUCAMONGA MIDDLE, both in Rancho Cucamonga).

## Performance

Measured on an Apple Silicon laptop after the index is built:

| Query | Time |
| --- | --- |
| The six README test cases | 0.01–4 ms each (extra credit is under 10 ms) |
| A single very common word ("school", "elementary") | about 20 ms |
| A word thousands of characters long | under 1 ms (no typo matching beyond the longest indexed word) |
| Slowest of all 34,779 name + city + state searches | 19 ms |

Times are the best of five runs. The reported "search took" time covers only the search. Loading and indexing happen before the timer starts, which the challenge allows. CI fails if a README query takes more than 25 ms or a common-word query more than 200 ms.

## Data

The data ships inside the package (`src/schools_tool/data/`), so the wheel works from any directory.

- `school_data.csv` is the NCES file `sl051b` for 2005-06. It is byte-for-byte the official download except for line endings. An earlier copy had replaced one byte with U+FFFD; that byte is restored.
- `name-abbr.csv` maps postal codes to state names, for searching by state name.

`dataset.load_schools` handles the file's quirks in one place, and the tests check each one:

| Issue | Handling |
| --- | --- |
| The encoding is Windows-1252. The one non-ASCII byte, 0x92, is the apostrophe in YUP’IK. The old code read it as ISO-8859-1, which turns that byte into a control character, and spelled the codec name with an en dash, which Python 3.17 rejects. | Read as `cp1252` |
| One school (NCESSCH 110003000297) has state `C` | Corrected to `DC`, the state of its district |
| One school (NCESSCH 050550000260) has city `\\UMAS` | Corrected to `DUMAS`, the city of its district and its other schools |
| 32 city values add a state or ZIP after a comma (`TUCSON, AZ`, `LITTLE ROCK, AR  72205`, `CAMP VERDE, ARIZONA`) or end in stray characters (`BRADENTON,`, `VOLUSIA COUNTY{`) | Everything after the first comma is dropped, since no real city name in the file has one, and stray trailing characters are removed |
| 33 cities are spelled several ways (`FT. LAUDERDALE` 25, `FT LAUDERDALE` 7, `FORT LAUDERDALE` 47; `ST./ST PETERSBURG`; `OPA-LOCKA/OPA LOCKA`) | Each city gets its most common spelling. Spellings that differ only in punctuation or FT/MT/ST abbreviations are treated as one |
| One school has city `N/A` | Treated as no city. It isn't counted toward cities and shows only its state in search results |
| 129 names contain double spaces (`POLARIS K  12 SCHOOL`) | Spaces collapsed |
| Columns could move or disappear in another year's file | Columns are found by header name. A missing column, a short row, a blank school ID, a byte that isn't Windows-1252 or a CSV parser error raises an error naming the file, and the line where the parser knows it |
| A school ID could repeat | The first row is kept |
| 1,096 schools have metro-centric locale `N` | Reported as their own group. `N` means NCES assigned no locale |

Counts include every school in the file, including the 541 closed since the previous survey (status 2) and the 959 not yet open (status 7), because the question asks about the data set.

`schools-tool counts --output-dir output` writes `summary.csv`, `schools_by_state.csv`, `schools_by_metro_locale.csv` and `schools_by_city.csv` for use downstream. `output/` is gitignored.

## Constraints

The challenge allows only `csv`, `time` and `itertools`. The counting and search logic sticks to `csv`, `time` and built-in types, with no third-party packages and no shortcuts such as `collections.Counter`, `difflib`, `re` or `math`. Other standard-library modules support that logic without doing any of it:
- `typing.NamedTuple` defines the `School` record.
- `collections.abc` is used for type hints.
- `pathlib` locates the bundled data and writes the CSV reports.
- `argparse`, `os` and `sys` run the command line.

If a reviewer reads the rule strictly, `School` could become a plain tuple and the CLI could be dropped without touching the answers.

## Repository layout

```
src/schools_tool/
  dataset.py         load and clean the CSV files
  count_schools.py   Part 1
  school_search.py   Part 2
  cli.py             schools-tool command (also python -m schools_tool)
  data/              bundled CSV files
tests/               pytest and hypothesis suite
docs/challenge.md    the original challenge
research/            exploratory notebooks, not part of the package
```

## Development

The project uses [uv](https://docs.astral.sh/uv/) with Python 3.15, pinned in `.python-version`.

```bash
uv sync               # create .venv with the package and dev tools
uv run pytest         # tests
uv run ruff check     # lint
uv run ruff format    # format (CI runs ruff format --check)
uv run mypy           # type check (strict)
uv build              # build the sdist and wheel into dist/
```

CI (`.github/workflows/ci.yml`) runs the test, lint, type check, format and build jobs on every pull request and every push to `main`. The build job installs the wheel in a clean environment and runs a search against the bundled data.

## Releasing

Versions follow [semantic versioning](https://semver.org/) and live in `pyproject.toml`.

1. On a branch, bump the version with `uv version --bump patch`, `minor` or `major`, then merge it.
2. Tag the merge commit with the new version and push the tag:
   ```bash
   git tag v0.1.1
   git push origin v0.1.1
   ```
3. `.github/workflows/release.yml` checks that the tag matches the version in `pyproject.toml`, runs the tests, builds the wheel and sdist, and attaches both to a GitHub Release.

Install a released wheel straight from its release page:

```bash
uv tool install https://github.com/evonnec/schools_tool/releases/download/v0.1.0/schools_tool-0.1.0-py3-none-any.whl
```

GitHub Packages has no Python registry, so PyPI is the package registry for this project. Publishing there is off by default. To turn it on:

1. On PyPI, add a trusted publisher for this repository with workflow `release.yml` and environment `pypi`.
2. Set the repository variable `PUBLISH_TO_PYPI` to `true`.
