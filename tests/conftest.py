import csv
from collections.abc import Callable
from pathlib import Path

import pytest

from schools_tool.dataset import School, load_schools
from schools_tool.school_search import SchoolIndex, default_index

NCES_HEADER = [
    "NCESSCH",
    "LEAID",
    "LEANM05",
    "SCHNAM05",
    "LCITY05",
    "LSTATE05",
    "LATCOD",
    "LONCOD",
    "MLOCALE",
    "ULOCALE",
    "status05",
]

# (school ID, name, city, state, metro locale)
SchoolRow = tuple[str, str, str, str, str]


@pytest.fixture(scope="session")
def bundled_schools() -> list[School]:
    return load_schools()


@pytest.fixture(scope="session")
def bundled_index() -> SchoolIndex:
    return default_index()


@pytest.fixture
def write_school_csv(tmp_path: Path) -> Callable[[list[SchoolRow]], Path]:
    """Write rows to a cp1252 CSV in the NCES layout and return its path."""

    def write(rows: list[SchoolRow]) -> Path:
        path = tmp_path / "school_data.csv"
        with path.open("w", encoding="cp1252", newline="") as school_file:
            writer = csv.writer(school_file)
            writer.writerow(NCES_HEADER)
            for school_id, name, city, state, locale in rows:
                writer.writerow(
                    [
                        school_id,
                        "0",
                        "AGENCY",
                        name,
                        city,
                        state,
                        "",
                        "",
                        locale,
                        "11",
                        "1",
                    ]
                )
        return path

    return write
