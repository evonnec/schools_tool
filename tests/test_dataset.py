from collections.abc import Callable
from pathlib import Path

import pytest

from schools_tool.dataset import (
    School,
    clean,
    clean_city,
    load_schools,
    load_state_names,
)

# The write_school_csv fixture: rows of (ID, name, city, state, locale)
WriteCsv = Callable[[list[tuple[str, str, str, str, str]]], Path]


class TestLoadSchools:
    def test_reads_one_school_per_row(self, write_school_csv: WriteCsv) -> None:
        path = write_school_csv(
            [
                ("1", "PINE SCHOOL", "DENVER", "CO", "1"),
                ("2", "OAK SCHOOL", "MESA", "AZ", "N"),
            ]
        )
        assert load_schools(path) == [
            School("1", "PINE SCHOOL", "DENVER", "CO", "1"),
            School("2", "OAK SCHOOL", "MESA", "AZ", "N"),
        ]

    def test_finds_columns_by_name(self, tmp_path: Path) -> None:
        path = tmp_path / "reordered.csv"
        path.write_text(
            "MLOCALE,LSTATE05,EXTRA,LCITY05,SCHNAM05,NCESSCH\n3,CO,x,DENVER,PINE SCHOOL,1\n"
        )
        assert load_schools(path) == [School("1", "PINE SCHOOL", "DENVER", "CO", "3")]

    def test_header_only_file_has_no_schools(self, write_school_csv: WriteCsv) -> None:
        assert load_schools(write_school_csv([])) == []

    def test_normalizes_case_and_spacing(self, write_school_csv: WriteCsv) -> None:
        path = write_school_csv(
            [("1", " polaris k  12 school ", "anchorage ", "ak", "1")]
        )
        assert load_schools(path) == [
            School("1", "POLARIS K 12 SCHOOL", "ANCHORAGE", "AK", "1")
        ]

    def test_corrects_known_bad_state(self, write_school_csv: WriteCsv) -> None:
        path = write_school_csv(
            [("1", "PRE-K INCENTIVE PROGRAM", "WASHINGTON", "C", "1")]
        )
        assert load_schools(path)[0].state == "DC"

    def test_cleans_city(self, write_school_csv: WriteCsv) -> None:
        path = write_school_csv([("1", "SCHOOL", "NEWNAN, GA.", "GA", "1")])
        assert load_schools(path)[0].city == "NEWNAN"

    def test_keeps_the_first_row_for_a_repeated_school_id(
        self, write_school_csv: WriteCsv
    ) -> None:
        path = write_school_csv(
            [
                ("1", "FIRST", "DENVER", "CO", "1"),
                ("1", "SECOND", "DENVER", "CO", "1"),
            ]
        )
        assert [school.name for school in load_schools(path)] == ["FIRST"]

    def test_reads_windows_1252(self, tmp_path: Path) -> None:
        path = tmp_path / "quote.csv"
        path.write_bytes(
            b"NCESSCH,SCHNAM05,LCITY05,LSTATE05,MLOCALE\n1,YUP\x92IK SCHOOL,BETHEL,AK,6\n"
        )
        assert load_schools(path)[0].name == "YUP’IK SCHOOL"

    def test_missing_column_is_an_error(self, tmp_path: Path) -> None:
        path = tmp_path / "missing.csv"
        path.write_text("NCESSCH,SCHNAM05,LCITY05\n1,PINE SCHOOL,DENVER\n")
        with pytest.raises(ValueError, match="missing columns LSTATE05, MLOCALE"):
            load_schools(path)

    def test_short_row_is_an_error_naming_the_line(self, tmp_path: Path) -> None:
        path = tmp_path / "short.csv"
        path.write_text(
            "NCESSCH,SCHNAM05,LCITY05,LSTATE05,MLOCALE\n1,A,B,CO,1\n2,PINE SCHOOL\n"
        )
        with pytest.raises(ValueError, match="line 3"):
            load_schools(path)

    def test_missing_file_is_an_error(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_schools(tmp_path / "nope.csv")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("  pine   school ", "PINE SCHOOL"), ("K  12", "K 12"), ("", "")],
)
def test_clean(raw: str, expected: str) -> None:
    assert clean(raw) == expected


@pytest.mark.parametrize(
    ("raw", "state", "expected"),
    [
        ("BRADENTON,", "FL", "BRADENTON"),
        ("TEEC NOS POS.", "AZ", "TEEC NOS POS"),
        ("VOLUSIA COUNTY{", "FL", "VOLUSIA COUNTY"),
        ("LOWMAN'", "ID", "LOWMAN"),
        ("TUCSON, AZ", "AZ", "TUCSON"),
        ("SURPRISE, AZ.", "AZ", "SURPRISE"),
        ("LAND O'LAKES,", "FL", "LAND O'LAKES"),
        ("ST. DAVID", "AZ", "ST. DAVID"),
        ("SPRINGFIELD, IL", "MO", "SPRINGFIELD, IL"),
    ],
)
def test_clean_city(raw: str, state: str, expected: str) -> None:
    assert clean_city(raw, state) == expected


def test_load_state_names(tmp_path: Path) -> None:
    path = tmp_path / "name-abbr.csv"
    path.write_text(
        '"State","Abbrev","Code"\n"Alabama","Ala.","AL"\n"District of Columbia","D.C.","dc"\n'
    )
    assert load_state_names(path) == {"AL": "ALABAMA", "DC": "DISTRICT OF COLUMBIA"}


class TestBundledData:
    """Checks on the dataset shipped in the package."""

    def test_row_count_and_unique_ids(self, bundled_schools: list[School]) -> None:
        assert len(bundled_schools) == 34779
        assert len({school.school_id for school in bundled_schools}) == 34779

    def test_every_state_is_a_known_postal_code(
        self, bundled_schools: list[School]
    ) -> None:
        known = load_state_names()
        assert {school.state for school in bundled_schools} <= known.keys()

    def test_no_blank_names_or_cities(self, bundled_schools: list[School]) -> None:
        assert all(school.name and school.city for school in bundled_schools)

    def test_cities_end_in_a_letter_or_digit(
        self, bundled_schools: list[School]
    ) -> None:
        assert all(school.city[-1].isalnum() for school in bundled_schools)

    def test_decodes_the_one_non_ascii_name(
        self, bundled_schools: list[School]
    ) -> None:
        non_ascii = [
            school.name for school in bundled_schools if not school.name.isascii()
        ]
        assert non_ascii == ["AYAPRUN ELITNAURVIK YUP’IK IMMERSION"]
