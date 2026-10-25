import csv
from pathlib import Path

import pytest

from schools_tool import count_schools

HEADER = "NCESSCH,LEAID,LEANM05,SCHNAM05,LCITY05,LSTATE05,LATCOD,LONCOD,MLOCALE,ULOCALE,status05"


def school_row(
    school_id: str, name: str, city: str, state: str, metro_locale: str = "1"
) -> list[str]:
    """An 11-column row shaped like input/school_data.csv."""
    return [
        school_id,
        "0",
        "AGENCY",
        name,
        city,
        state,
        "0",
        "0",
        metro_locale,
        "11",
        "1",
    ]


@pytest.fixture
def write_school_csv(tmp_path: Path):
    """Write rows under the school_data.csv header and return the file path."""

    def write(rows: list[list[str]]) -> str:
        path = tmp_path / "school_data.csv"
        with path.open("w", newline="", encoding="iso-8859-1") as f:
            f.write(HEADER + "\n")
            csv.writer(f).writerows(rows)
        return str(path)

    return write


ROWS = [
    school_row("1", "LINCOLN ELEMENTARY", "SPRINGFIELD", "IL", metro_locale="2"),
    school_row("2", "WASHINGTON HIGH", "SPRINGFIELD", "IL", metro_locale="2"),
    school_row("3", "SPRINGFIELD MIDDLE", "SPRINGFIELD", "CO", metro_locale="N"),
    school_row("4", "PINE SCHOOL", "DENVER", "CO", metro_locale="1"),
]


class TestGetDf:
    def test_skips_header_and_returns_every_row(self, write_school_csv) -> None:
        path = write_school_csv(ROWS)
        assert count_schools.get_df(path) == ROWS

    def test_rejects_rows_with_the_wrong_number_of_columns(
        self, write_school_csv
    ) -> None:
        path = write_school_csv([["1", "too", "short"]])
        with pytest.raises(ValueError):
            count_schools.get_df(path)

    def test_header_only_file_has_no_rows(self, write_school_csv) -> None:
        assert count_schools.get_df(write_school_csv([])) == []


class TestCounts:
    def test_total_school_count(self) -> None:
        assert count_schools.total_school_count(ROWS) == 4

    def test_total_school_count_ignores_duplicate_ids(self) -> None:
        duplicate = school_row("1", "LINCOLN ELEMENTARY", "SPRINGFIELD", "IL")
        assert count_schools.total_school_count([*ROWS, duplicate]) == 4

    def test_schools_per_state_count(self) -> None:
        assert count_schools.schools_per_state_count(ROWS) == {
            "IL": {"school_count": 2},
            "CO": {"school_count": 2},
        }

    def test_schools_per_metro_count(self) -> None:
        assert count_schools.schools_per_metro_count(ROWS) == {
            "2": {"school_count": 2},
            "N": {"school_count": 1},
            "1": {"school_count": 1},
        }

    def test_cities_are_keyed_by_city_and_state_and_ranked(self) -> None:
        assert count_schools.schools_per_city_count(ROWS) == [
            ("springfield|il", {"school_count": 2}),
            ("springfield|co", {"school_count": 1}),
            ("denver|co", {"school_count": 1}),
        ]

    def test_empty_input(self) -> None:
        assert count_schools.total_school_count([]) == 0
        assert count_schools.schools_per_state_count([]) == {}
        assert count_schools.schools_per_city_count([]) == []


def test_format_result() -> None:
    result = count_schools.format_result(
        {"IL": {"school_count": 2}, "CO": {"school_count": 1}}
    )
    assert result == "IL : {'school_count': 2}\nCO : {'school_count': 1}\n"


@pytest.mark.usefixtures("in_repo_root")
class TestSchoolData:
    """Counts over the real input/school_data.csv."""

    def test_total_schools(self) -> None:
        assert count_schools.total_school_count(count_schools.get_df()) == 34779

    def test_schools_by_state(self) -> None:
        by_state = count_schools.schools_per_state_count(count_schools.get_df())
        assert len(by_state) == 21
        assert by_state["CA"] == {"school_count": 9969}

    def test_schools_by_metro(self) -> None:
        by_metro = count_schools.schools_per_metro_count(count_schools.get_df())
        assert len(by_metro) == 9
        assert sum(count["school_count"] for count in by_metro.values()) == 34779

    def test_schools_by_city(self) -> None:
        by_city = count_schools.schools_per_city_count(count_schools.get_df())
        assert len(by_city) == 5752
        assert by_city[0] == ("chicago|il", {"school_count": 657})

    def test_print_counts(self, capsys: pytest.CaptureFixture[str]) -> None:
        count_schools.print_counts()
        out = capsys.readouterr().out
        assert "total schools:\n34779\n" in out
        assert "CA : {'school_count': 9969}" in out
        assert "('chicago|il', {'school_count': 657})" in out
        assert "number of unique cities with one school or more:\n5752\n" in out
