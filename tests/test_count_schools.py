import csv
from pathlib import Path

import pytest

from schools_tool import count_schools
from schools_tool.dataset import School

SCHOOLS = [
    School("1", "LINCOLN ELEMENTARY", "SPRINGFIELD", "IL", "2"),
    School("2", "WASHINGTON HIGH", "SPRINGFIELD", "IL", "2"),
    School("3", "SPRINGFIELD MIDDLE", "SPRINGFIELD", "CO", "N"),
    School("4", "PINE SCHOOL", "DENVER", "CO", "1"),
]


class TestCounts:
    def test_total_school_count(self) -> None:
        assert count_schools.total_school_count(SCHOOLS) == 4

    def test_total_counts_records_like_the_other_counts(self) -> None:
        # load_schools keeps one record per school ID; the counts all agree
        # on whatever list they are given.
        doubled = [*SCHOOLS, SCHOOLS[0]]
        assert count_schools.total_school_count(doubled) == 5
        assert sum(count_schools.schools_per_state(doubled).values()) == 5

    def test_total_accepts_any_iterable(self) -> None:
        assert count_schools.total_school_count(iter(SCHOOLS)) == 4

    def test_schools_without_a_city_are_left_out_of_city_counts(self) -> None:
        schools = [*SCHOOLS, School("5", "ALTERNATIVE EDUCATION", "", "FL", "N")]
        assert count_schools.unique_city_count(schools) == 3
        assert count_schools.total_school_count(schools) == 5
        assert count_schools.schools_per_state(schools)["FL"] == 1

    def test_schools_per_state(self) -> None:
        assert count_schools.schools_per_state(SCHOOLS) == {"IL": 2, "CO": 2}

    def test_schools_per_metro_locale(self) -> None:
        assert count_schools.schools_per_metro_locale(SCHOOLS) == {
            "2": 2,
            "N": 1,
            "1": 1,
        }

    def test_cities_are_city_and_state_pairs(self) -> None:
        assert count_schools.schools_per_city(SCHOOLS) == {
            ("SPRINGFIELD", "IL"): 2,
            ("SPRINGFIELD", "CO"): 1,
            ("DENVER", "CO"): 1,
        }
        assert count_schools.unique_city_count(SCHOOLS) == 3

    def test_city_with_most_schools(self) -> None:
        assert count_schools.cities_with_most_schools(SCHOOLS) == (
            [("SPRINGFIELD", "IL")],
            2,
        )

    def test_tied_cities_are_all_reported_alphabetically(self) -> None:
        assert count_schools.cities_with_most_schools(SCHOOLS[2:]) == (
            [("DENVER", "CO"), ("SPRINGFIELD", "CO")],
            1,
        )

    def test_no_schools(self) -> None:
        assert count_schools.total_school_count([]) == 0
        assert count_schools.schools_per_state([]) == {}
        assert count_schools.cities_with_most_schools([]) == ([], 0)
        assert count_schools.unique_city_count([]) == 0


class TestFormatCounts:
    def test_matches_the_readme_format(self) -> None:
        assert count_schools.format_counts(SCHOOLS) == "\n".join(
            [
                "Total Schools: 4",
                "Schools by State:",
                "CO: 2",
                "IL: 2",
                "Schools by Metro-centric locale:",
                "1: 1",
                "2: 2",
                "N: 1",
                "City with most schools: SPRINGFIELD, IL (2 schools)",
                "Unique cities with at least one school: 3",
            ]
        )

    def test_ties(self) -> None:
        report = count_schools.format_counts(SCHOOLS[2:])
        assert (
            "Cities with most schools: DENVER, CO; SPRINGFIELD, CO (1 schools each)"
            in report.splitlines()
        )

    def test_no_schools(self) -> None:
        assert count_schools.format_counts([]).splitlines() == [
            "Total Schools: 0",
            "Schools by State:",
            "Schools by Metro-centric locale:",
            "City with most schools: none",
            "Unique cities with at least one school: 0",
        ]


def test_print_counts_prints_the_report(capsys: pytest.CaptureFixture[str]) -> None:
    count_schools.print_counts(SCHOOLS)
    assert capsys.readouterr().out == count_schools.format_counts(SCHOOLS) + "\n"


def test_write_counts(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    written = count_schools.write_counts(SCHOOLS, output_dir)

    def read(name: str) -> list[list[str]]:
        with (output_dir / name).open(newline="") as f:
            return list(csv.reader(f))

    assert sorted(path.name for path in written) == [
        "schools_by_city.csv",
        "schools_by_metro_locale.csv",
        "schools_by_state.csv",
        "summary.csv",
    ]
    assert read("summary.csv") == [
        ["metric", "value"],
        ["total_schools", "4"],
        ["unique_cities", "3"],
        ["most_schools_in_a_city", "2"],
        ["cities_with_most_schools", "SPRINGFIELD, IL"],
    ]
    assert read("schools_by_state.csv") == [
        ["state", "school_count"],
        ["CO", "2"],
        ["IL", "2"],
    ]
    assert read("schools_by_city.csv") == [
        ["city", "state", "school_count"],
        ["SPRINGFIELD", "IL", "2"],
        ["DENVER", "CO", "1"],
        ["SPRINGFIELD", "CO", "1"],
    ]


class TestBundledData:
    """The Part 1 answers for the dataset shipped in the package."""

    def test_total(self, bundled_schools: list[School]) -> None:
        assert count_schools.total_school_count(bundled_schools) == 34779

    def test_states(self, bundled_schools: list[School]) -> None:
        per_state = count_schools.schools_per_state(bundled_schools)
        assert len(per_state) == 20
        assert per_state["CA"] == 9969
        assert per_state["DC"] == 230
        assert "C" not in per_state

    def test_metro_locales(self, bundled_schools: list[School]) -> None:
        per_locale = count_schools.schools_per_metro_locale(bundled_schools)
        assert sorted(per_locale) == ["1", "2", "3", "4", "5", "6", "7", "8", "N"]
        assert per_locale["N"] == 1096
        assert sum(per_locale.values()) == 34779

    def test_city_with_most_schools(self, bundled_schools: list[School]) -> None:
        assert count_schools.cities_with_most_schools(bundled_schools) == (
            [("CHICAGO", "IL")],
            657,
        )

    def test_unique_cities(self, bundled_schools: list[School]) -> None:
        assert count_schools.unique_city_count(bundled_schools) == 5670

    def test_print_counts_loads_the_bundled_data(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        count_schools.print_counts()
        lines = capsys.readouterr().out.splitlines()
        assert lines[0] == "Total Schools: 34779"
        assert "City with most schools: CHICAGO, IL (657 schools)" in lines
        assert lines[-1] == "Unique cities with at least one school: 5670"
