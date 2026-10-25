"""Load and clean the NCES 2005-06 school file and the state name table."""

import csv
from pathlib import Path
from typing import NamedTuple

DATA_DIR = Path(__file__).parent / "data"
SCHOOL_DATA_CSV = DATA_DIR / "school_data.csv"
STATE_NAMES_CSV = DATA_DIR / "name-abbr.csv"

# The NCES download is Windows-1252. Its only non-ASCII byte is 0x92, the
# right single quote in "YUP’IK", which ISO-8859-1 reads as a control code.
SCHOOL_DATA_ENCODING = "cp1252"

# Column names from the file layout in the dataset documentation (sl051bgen).
SCHOOL_ID = "NCESSCH"
SCHOOL_NAME = "SCHNAM05"
CITY = "LCITY05"
STATE = "LSTATE05"
METRO_LOCALE = "MLOCALE"
REQUIRED_COLUMNS = (SCHOOL_ID, SCHOOL_NAME, CITY, STATE, METRO_LOCALE)

# Known bad values in the source file. NCESSCH 110003000297 (PRE-K INCENTIVE
# PROGRAM, WASHINGTON) has state "C"; its district, 1100030, is in DC.
STATE_CORRECTIONS = {"C": "DC"}
# NCESSCH 050550000260 (CENTRAL ELEMENTARY SCHOOL) has city "\\UMAS"; its
# district, DUMAS, and every other school in it are in DUMAS.
CITY_CORRECTIONS = {"050550000260": "DUMAS"}
# City values that mean the city is unknown.
MISSING_CITIES = {"N/A"}

# 32 city values add a state or ZIP after a comma ("TUCSON, AZ", "LITTLE
# ROCK, AR  72205", "CAMP VERDE, ARIZONA") or end in stray characters
# ("BRADENTON,", "VOLUSIA COUNTY{"). No city name in the file needs a comma.
CITY_TRAILING_JUNK = " .,;:'{}"

# Abbreviations that make one city look like several: FT. LAUDERDALE,
# FT LAUDERDALE and FORT LAUDERDALE; W TERRE HAUTE and WEST TERRE HAUTE.
CITY_ABBREVIATIONS = {
    "E": "EAST",
    "FT": "FORT",
    "HTS": "HEIGHTS",
    "MT": "MOUNT",
    "N": "NORTH",
    "S": "SOUTH",
    "ST": "SAINT",
    "W": "WEST",
}


class School(NamedTuple):
    school_id: str
    name: str
    city: str
    state: str
    metro_locale: str


def clean(value: str) -> str:
    """Upper-case, trim, and collapse runs of spaces ("K  12" -> "K 12")."""
    return " ".join(value.upper().split())


def clean_city(value: str) -> str:
    """Drop anything after a comma and stray trailing characters
    ("LITTLE ROCK, AR  72205" -> "LITTLE ROCK", "BRADENTON," -> "BRADENTON")."""
    city = clean(value).split(",")[0].rstrip(CITY_TRAILING_JUNK)
    return "" if city in MISSING_CITIES else city


def city_key(city: str) -> str:
    """The city name with abbreviations expanded and punctuation and spaces
    dropped, so spellings of one city compare equal ("FT. LAUDERDALE" ->
    "FORTLAUDERDALE", "LAND O' LAKES" and "LAND O'LAKES" -> "LANDOLAKES")."""
    # Drop apostrophes and periods rather than splitting on them, so the S
    # in MARY'S and the letters of N.A.S. don't read as abbreviations.
    joined = city.replace("'", "").replace(".", "")
    words = "".join(char if char.isalnum() else " " for char in joined).split()
    return "".join(CITY_ABBREVIATIONS.get(word, word) for word in words)


def unify_city_spellings(schools: list[School]) -> list[School]:
    """Spell each city the way most of its schools do, so FT. LAUDERDALE,
    FT LAUDERDALE and FORT LAUDERDALE are one city. Ties go to the longer,
    usually unabbreviated, spelling."""
    spellings: dict[tuple[str, str], dict[str, int]] = {}
    for school in schools:
        counts = spellings.setdefault((city_key(school.city), school.state), {})
        counts[school.city] = counts.get(school.city, 0) + 1

    preferred = {}
    for group, counts in spellings.items():
        preferred[group] = max(
            counts, key=lambda spelling: (counts[spelling], len(spelling), spelling)
        )
    return [
        school._replace(city=preferred[city_key(school.city), school.state])
        for school in schools
    ]


def load_schools(path: str | Path = SCHOOL_DATA_CSV) -> list[School]:
    """Read the school file into one cleaned School per school ID.

    Raises ValueError, naming the file and line where it can, if the file is
    not Windows-1252 CSV, lacks a required column, or has a short row or a
    blank school ID, so a malformed file fails loudly instead of being
    counted wrong. A row that repeats an earlier school ID is dropped.
    """
    with open(path, encoding=SCHOOL_DATA_ENCODING, newline="") as school_file:
        reader = csv.DictReader(school_file)
        try:
            schools = read_schools(reader, path)
        except UnicodeDecodeError as error:
            raise ValueError(
                f"{path}: not Windows-1252 text ({error.reason})"
            ) from error
        except csv.Error as error:
            raise ValueError(f"{path}, line {reader.line_num}: {error}") from error
    return unify_city_spellings(schools)


def read_schools(reader: csv.DictReader[str], path: str | Path) -> list[School]:
    missing = [
        name for name in REQUIRED_COLUMNS if name not in (reader.fieldnames or [])
    ]
    if missing:
        raise ValueError(f"{path}: missing columns {', '.join(missing)}")

    schools = []
    seen_ids = set()
    for row in reader:
        if any(row[name] is None for name in REQUIRED_COLUMNS):
            raise ValueError(f"{path}, line {reader.line_num}: row has too few columns")
        school_id = row[SCHOOL_ID].strip()
        if not school_id:
            raise ValueError(f"{path}, line {reader.line_num}: blank {SCHOOL_ID}")
        if school_id in seen_ids:
            continue
        seen_ids.add(school_id)
        state = clean(row[STATE])
        schools.append(
            School(
                school_id=school_id,
                name=clean(row[SCHOOL_NAME]),
                city=CITY_CORRECTIONS.get(school_id) or clean_city(row[CITY]),
                state=STATE_CORRECTIONS.get(state, state),
                metro_locale=clean(row[METRO_LOCALE]),
            )
        )
    return schools


def load_state_names(path: str | Path = STATE_NAMES_CSV) -> dict[str, str]:
    """Map postal codes to state names, e.g. "AL" -> "ALABAMA"."""
    with open(path, encoding="utf-8", newline="") as states_file:
        return {
            clean(row["Code"]): clean(row["State"])
            for row in csv.DictReader(states_file)
        }
