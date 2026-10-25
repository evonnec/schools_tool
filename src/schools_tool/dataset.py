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

# Fourteen city values end in stray characters or repeat the state
# ("BRADENTON,", "VOLUSIA COUNTY{", "TUCSON, AZ"). Uncleaned, twelve of them
# would count as cities separate from the one they belong to.
CITY_TRAILING_JUNK = " .,;:'{}"


class School(NamedTuple):
    school_id: str
    name: str
    city: str
    state: str
    metro_locale: str


def clean(value: str) -> str:
    """Upper-case, trim, and collapse runs of spaces ("K  12" -> "K 12")."""
    return " ".join(value.upper().split())


def clean_city(value: str, state: str) -> str:
    """Drop stray trailing punctuation and a repeated state ("NEWNAN, GA." -> "NEWNAN")."""
    city = clean(value).rstrip(CITY_TRAILING_JUNK)
    state_suffix = f", {state}"
    if city.endswith(state_suffix):
        city = city.removesuffix(state_suffix)
    return city


def load_schools(path: str | Path = SCHOOL_DATA_CSV) -> list[School]:
    """Read the school file into one School per school ID.

    Raises ValueError if a required column is missing or a row is short, so a
    malformed file fails loudly instead of being counted wrong. Rows that
    repeat an earlier school ID are dropped.
    """
    schools = []
    seen_ids = set()
    with open(path, encoding=SCHOOL_DATA_ENCODING, newline="") as school_file:
        reader = csv.DictReader(school_file)
        missing = [
            name for name in REQUIRED_COLUMNS if name not in (reader.fieldnames or [])
        ]
        if missing:
            raise ValueError(f"{path}: missing columns {', '.join(missing)}")

        for row in reader:
            if any(row[name] is None for name in REQUIRED_COLUMNS):
                raise ValueError(
                    f"{path}, line {reader.line_num}: row has too few columns"
                )
            school_id = row[SCHOOL_ID].strip()
            if school_id in seen_ids:
                continue
            seen_ids.add(school_id)
            state = clean(row[STATE])
            state = STATE_CORRECTIONS.get(state, state)
            schools.append(
                School(
                    school_id=school_id,
                    name=clean(row[SCHOOL_NAME]),
                    city=clean_city(row[CITY], state),
                    state=state,
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
