from collections.abc import Callable
from pathlib import Path

import pytest

from schools_tool.dataset import (
    School,
    city_key,
    clean,
    clean_city,
    load_schools,
    load_state_names,
    unify_city_spellings,
)

# The write_school_csv fixture: rows of (ID, name, city, state, locale)
WriteCsv = Callable[[list[tuple[str, str, str, str, str]]], Path]
HEADER = "NCESSCH,SCHNAM05,LCITY05,LSTATE05,MLOCALE\n"


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

    def test_corrects_known_bad_values(self, write_school_csv: WriteCsv) -> None:
        path = write_school_csv(
            [
                ("110003000297", "PRE-K INCENTIVE PROGRAM", "WASHINGTON", "C", "1"),
                ("050550000260", "CENTRAL ELEMENTARY SCHOOL", "\\\\UMAS", "AR", "6"),
            ]
        )
        assert [(school.city, school.state) for school in load_schools(path)] == [
            ("WASHINGTON", "DC"),
            ("DUMAS", "AR"),
        ]

    def test_cleans_cities(self, write_school_csv: WriteCsv) -> None:
        path = write_school_csv(
            [
                ("1", "A", "NEWNAN, GA.", "GA", "1"),
                ("2", "B", "LITTLE ROCK, AR  72205", "AR", "1"),
                ("3", "C", "N/A", "FL", "1"),
            ]
        )
        assert [school.city for school in load_schools(path)] == [
            "NEWNAN",
            "LITTLE ROCK",
            "",
        ]

    def test_unifies_city_spellings(self, write_school_csv: WriteCsv) -> None:
        path = write_school_csv(
            [
                ("1", "A", "FT. LAUDERDALE", "FL", "1"),
                ("2", "B", "FORT LAUDERDALE", "FL", "1"),
                ("3", "C", "FORT LAUDERDALE", "FL", "1"),
            ]
        )
        assert {school.city for school in load_schools(path)} == {"FORT LAUDERDALE"}

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
        path.write_bytes(HEADER.encode() + b"1,YUP\x92IK SCHOOL,BETHEL,AK,6\n")
        assert load_schools(path)[0].name == "YUP’IK SCHOOL"

    def test_missing_column_is_an_error(self, tmp_path: Path) -> None:
        path = tmp_path / "missing.csv"
        path.write_text("NCESSCH,SCHNAM05,LCITY05\n1,PINE SCHOOL,DENVER\n")
        with pytest.raises(ValueError, match="missing columns LSTATE05, MLOCALE"):
            load_schools(path)

    def test_short_row_is_an_error_naming_the_line(self, tmp_path: Path) -> None:
        path = tmp_path / "short.csv"
        path.write_text(HEADER + "1,A,B,CO,1\n2,PINE SCHOOL\n")
        with pytest.raises(ValueError, match="line 3"):
            load_schools(path)

    def test_blank_school_id_is_an_error(self, tmp_path: Path) -> None:
        path = tmp_path / "blank.csv"
        path.write_text(HEADER + "1,A,B,CO,1\n ,PINE SCHOOL,DENVER,CO,1\n")
        with pytest.raises(ValueError, match="line 3: blank NCESSCH"):
            load_schools(path)

    def test_non_windows_1252_bytes_are_an_error(self, tmp_path: Path) -> None:
        path = tmp_path / "bytes.csv"
        path.write_bytes(HEADER.encode() + b"1,BAD \x81 BYTE,DENVER,CO,1\n")
        with pytest.raises(ValueError, match="not Windows-1252"):
            load_schools(path)

    def test_csv_parser_errors_name_the_file(self, tmp_path: Path) -> None:
        path = tmp_path / "huge.csv"
        path.write_text(HEADER + f'1,"{"X" * 200_000}",DENVER,CO,1\n')
        with pytest.raises(ValueError, match="huge.csv, line"):
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
    ("raw", "expected"),
    [
        ("BRADENTON,", "BRADENTON"),
        ("TEEC NOS POS.", "TEEC NOS POS"),
        ("VOLUSIA COUNTY{", "VOLUSIA COUNTY"),
        ("LOWMAN'", "LOWMAN"),
        ("TUCSON, AZ", "TUCSON"),
        ("SURPRISE, AZ.", "SURPRISE"),
        ("LITTLE ROCK, AR  72205", "LITTLE ROCK"),
        ("ROGERS,, AR  72756", "ROGERS"),
        ("CAMP VERDE, ARIZONA", "CAMP VERDE"),
        ("LAND O'LAKES,", "LAND O'LAKES"),
        ("ST. DAVID", "ST. DAVID"),
        ("N/A", ""),
        ("", ""),
    ],
)
def test_clean_city(raw: str, expected: str) -> None:
    assert clean_city(raw) == expected


@pytest.mark.parametrize(
    ("city", "key"),
    [
        ("FT. LAUDERDALE", "FORTLAUDERDALE"),
        ("MT VERNON", "MOUNTVERNON"),
        ("ST. MARY'S", "SAINTMARYS"),
        ("OPA-LOCKA", "OPALOCKA"),
        ("LAND O' LAKES", "LANDOLAKES"),
        ("LAND O'LAKES", "LANDOLAKES"),
        ("W TERRE HAUTE", "WESTTERREHAUTE"),
        ("DE KALB", "DEKALB"),
        ("STERLING", "STERLING"),
    ],
)
def test_city_key(city: str, key: str) -> None:
    assert city_key(city) == key


class TestUnifyCitySpellings:
    def test_most_common_spelling_wins(self) -> None:
        schools = [
            School("1", "A", "ST AUGUSTINE", "FL", "1"),
            School("2", "B", "ST. AUGUSTINE", "FL", "1"),
            School("3", "C", "ST AUGUSTINE", "FL", "1"),
        ]
        assert {school.city for school in unify_city_spellings(schools)} == {
            "ST AUGUSTINE"
        }

    def test_full_spelling_wins_a_tie(self) -> None:
        schools = [
            School("1", "A", "ST PAUL", "AR", "1"),
            School("2", "B", "SAINT PAUL", "AR", "1"),
        ]
        assert {school.city for school in unify_city_spellings(schools)} == {
            "SAINT PAUL"
        }
        schools = [
            School("1", "A", "ST. MARY'S", "AK", "1"),
            School("2", "B", "SAINT MARY'S", "AK", "1"),
        ]
        assert {school.city for school in unify_city_spellings(schools)} == {
            "SAINT MARY'S"
        }

    def test_states_are_kept_apart(self) -> None:
        schools = [
            School("1", "A", "MT VERNON", "AL", "1"),
            School("2", "B", "MOUNT VERNON", "IL", "1"),
        ]
        assert [school.city for school in unify_city_spellings(schools)] == [
            "MT VERNON",
            "MOUNT VERNON",
        ]


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

    def test_no_blank_names(self, bundled_schools: list[School]) -> None:
        assert all(school.name for school in bundled_schools)

    def test_one_school_has_no_known_city(self, bundled_schools: list[School]) -> None:
        assert [school.school_id for school in bundled_schools if not school.city] == [
            "120129004987"
        ]

    def test_cities_are_clean(self, bundled_schools: list[School]) -> None:
        cities = {school.city for school in bundled_schools if school.city}
        assert all(city[0].isalpha() and city[-1].isalnum() for city in cities)
        assert not [city for city in cities if "," in city]

    def test_each_city_has_one_spelling(self, bundled_schools: list[School]) -> None:
        spellings: dict[tuple[str, str], set[str]] = {}
        for school in bundled_schools:
            spellings.setdefault((city_key(school.city), school.state), set()).add(
                school.city
            )
        assert all(len(names) == 1 for names in spellings.values())

    def test_decodes_the_one_non_ascii_name(
        self, bundled_schools: list[School]
    ) -> None:
        non_ascii = [
            school.name for school in bundled_schools if not school.name.isascii()
        ]
        assert non_ascii == ["AYAPRUN ELITNAURVIK YUP’IK IMMERSION"]
