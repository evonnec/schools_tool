import time
from pathlib import Path

import pytest

from schools_tool import school_search

STATES = {"AL": "ALABAMA", "AK": "ALASKA"}
SEQUOYAH = ["SEQUOYAH SCHOOL - CHALKVILLE CAMPUS", "PINSON", "AL"]
KUSKOKWIM = ["TOP OF THE KUSKOKWIM SCHOOL", "NIKOLAI", "AK"]
DATAFRAME = [SEQUOYAH, KUSKOKWIM]


def test_map_abbreviation_to_state(tmp_path: Path) -> None:
    path = tmp_path / "name-abbr.csv"
    path.write_text(
        '"State","Abbrev","Code"\n"Alabama","Ala.","AL"\n"Alaska","Alaska","ak"\n'
    )
    assert school_search.map_abbreviation_to_state(str(path)) == {
        "AL": "ALABAMA",
        "AK": "ALASKA",
    }


class TestIsWordInDataframeRow:
    @pytest.mark.parametrize(
        ("word", "expected"),
        [
            ("KUSKOKWIM", True),
            ("kuskokwim", True),
            ("Kusko", True),
            ("Nikolai", True),
            ("alaska", True),
            ("AK", False),
            ("pinson", False),
        ],
    )
    def test_matches_school_city_and_full_state_name(
        self, word: str, expected: bool
    ) -> None:
        assert (
            school_search.is_word_in_dataframe_row(KUSKOKWIM, word, STATES) is expected
        )

    def test_state_missing_from_map_still_searches_school_and_city(self) -> None:
        row = ["TOP OF THE KUSKOKWIM SCHOOL", "NIKOLAI", "ZZ"]
        assert school_search.is_word_in_dataframe_row(row, "KUSKOKWIM", STATES)
        assert not school_search.is_word_in_dataframe_row(row, "ZZ", STATES)


class TestSearchFullSearchTermWithinDataframe:
    def search(self, term: str) -> list[list[str]]:
        return school_search.search_full_search_term_within_dataframe(
            DATAFRAME, term, STATES
        )

    def test_empty_search_term(self) -> None:
        assert self.search("") == []

    def test_two_words_match(self) -> None:
        assert self.search("KUSKOKWIM NIKOLAI") == [KUSKOKWIM]

    def test_no_results_for_any_word(self) -> None:
        assert self.search("FOOBAR BAZBAT") == []

    def test_words_without_matches_are_ignored(self) -> None:
        assert self.search("FOOBAR SEQUOYAH BAZBAT") == [SEQUOYAH]

    def test_more_matching_words_rank_higher(self) -> None:
        assert self.search("school nikolai") == [KUSKOKWIM, SEQUOYAH]

    def test_school_counts_for_less_than_other_words(self) -> None:
        dataframe = [
            ["PINE SCHOOL", "NIKOLAI", "AK"],
            ["PINE ACADEMY", "NIKOLAI", "AK"],
        ]
        results = school_search.search_full_search_term_within_dataframe(
            dataframe, "pine school academy", STATES
        )
        # "academy" is worth a full point, "school" only half a point
        assert results == [dataframe[1], dataframe[0]]


def test_format_result() -> None:
    assert school_search.format_result(SEQUOYAH) == (
        "SEQUOYAH SCHOOL - CHALKVILLE CAMPUS\nPINSON, AL"
    )


# README "Test Cases": the expected schools must be the top hits, in any order.
README_CASES = [
    (
        "elementary school highland park",
        {
            "HIGHLAND PARK ELEMENTARY SCHOOL\nMUSCLE SHOALS, AL",
            "HIGHLAND PARK ELEMENTARY SCHOOL\nPUEBLO, CO",
        },
    ),
    ("jefferson belleville", {"JEFFERSON ELEM SCHOOL\nBELLEVILLE, IL"}),
    ("riverside school 44", {"RIVERSIDE SCHOOL 44\nINDIANAPOLIS, IN"}),
    (
        "granada charter school",
        {
            "NORTH VALLEY CHARTER ACADEMY\nGRANADA HILLS, CA",
            "GRANADA HILLS CHARTER HIGH\nGRANADA HILLS, CA",
        },
    ),
    ("foley high alabama", {"FOLEY HIGH SCHOOL\nFOLEY, AL"}),
    ("KUSKOKWIM", {"TOP OF THE KUSKOKWIM SCHOOL\nNIKOLAI, AK"}),
]


@pytest.mark.usefixtures("in_repo_root")
class TestReadmeCases:
    @pytest.mark.parametrize(("query", "expected_top"), README_CASES)
    def test_expected_schools_are_the_top_hits(
        self, query: str, expected_top: set[str]
    ) -> None:
        results = school_search.search_school_results(query)
        top = {school_search.format_result(row) for row in results[: len(expected_top)]}
        assert top == expected_top

    @pytest.mark.parametrize(("query", "expected_top"), README_CASES[:-1])
    def test_returns_at_least_three_results(
        self, query: str, expected_top: set[str]
    ) -> None:
        assert len(school_search.search_school_results(query)) >= 3

    def test_kuskokwim_returns_a_single_result(self) -> None:
        assert len(school_search.search_school_results("KUSKOKWIM")) == 1

    @pytest.mark.parametrize(("query", "expected_top"), README_CASES)
    def test_search_runs_in_under_200ms(
        self, query: str, expected_top: set[str]
    ) -> None:
        states = school_search.map_abbreviation_to_state()
        dataframe = school_search.get_school_data_dataframes(states)
        timings = []
        for _ in range(3):
            start = time.perf_counter()
            school_search.search_full_search_term_within_dataframe(
                dataframe, query, states
            )
            timings.append(time.perf_counter() - start)
        assert min(timings) < 0.2

    def test_search_schools_prints_the_top_three(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        school_search.search_schools("foley high alabama")
        lines = capsys.readouterr().out.splitlines()
        # search_school_results prints debug timings before the results
        header_index = next(
            i for i, line in enumerate(lines) if line.startswith("Results for")
        )
        results = lines[header_index:]
        assert results[0].startswith('Results for "foley high alabama" (search took: ')
        assert results[1:3] == ["1. FOLEY HIGH SCHOOL", "FOLEY, AL"]
        assert [line[:3] for line in results[1::2]] == ["1. ", "2. ", "3. "]
