import time

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from schools_tool import school_search
from schools_tool.dataset import School
from schools_tool.school_search import (
    SchoolIndex,
    abbreviation_equivalents,
    format_results,
    one_edit_away,
    search_schools,
    tokenize,
)

STATES = {
    "AL": "ALABAMA",
    "AK": "ALASKA",
    "DC": "DISTRICT OF COLUMBIA",
    "IL": "ILLINOIS",
}


def build_index(*rows: tuple[str, str, str]) -> SchoolIndex:
    """An index over (name, city, state) rows."""
    schools = [
        School(f"{i:03}", name, city, state, "1")
        for i, (name, city, state) in enumerate(rows)
    ]
    return SchoolIndex(schools, STATES)


def lines(results: list[School]) -> list[str]:
    return [f"{school.name}, {school.city}, {school.state}" for school in results]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Highland Park", ["HIGHLAND", "PARK"]),
        ("COLLINS-RIVERSIDE MIDDLE", ["COLLINS", "RIVERSIDE", "MIDDLE"]),
        ("ST. MARY'S", ["ST", "MARYS"]),
        ("YUP’IK", ["YUPIK"]),
        ("riverside school 44", ["RIVERSIDE", "SCHOOL", "44"]),
        ("CABRILLO (JUAN RODRIGUEZ) HIGH", ["CABRILLO", "JUAN", "RODRIGUEZ", "HIGH"]),
        ("  !!  ", []),
        ("", []),
    ],
)
def test_tokenize(text: str, expected: list[str]) -> None:
    assert tokenize(text) == expected


def test_one_edit_away() -> None:
    edits = one_edit_away("CAT")
    assert {"AT", "ACT", "BAT", "CART", "CATS"} <= edits
    assert "CAT" not in edits
    assert "DOG" not in edits


def test_abbreviation_equivalents() -> None:
    equivalents = abbreviation_equivalents()
    assert equivalents["ELEM"] == ["ELEMENTARY"]
    assert equivalents["ELEMENTARY"] == ["ELEM"]
    assert equivalents["HS"] == ["HIGH", "SCHOOL"]
    assert sorted(equivalents["SCHOOL"]) == ["HS", "SCH", "SCHL"]


class TestMatching:
    def test_exact_word_beats_prefix(self) -> None:
        index = build_index(
            ("HIGHLAND SCHOOL", "MESA", "AZ"), ("HIGH SCHOOL", "MESA", "AZ")
        )
        assert lines(index.search("high")) == [
            "HIGH SCHOOL, MESA, AZ",
            "HIGHLAND SCHOOL, MESA, AZ",
        ]

    def test_prefix_needs_three_letters(self) -> None:
        index = build_index(("INDIAN TRAIL SCHOOL", "MESA", "AZ"))
        assert index.search("in") == []
        assert lines(index.search("ind")) == ["INDIAN TRAIL SCHOOL, MESA, AZ"]

    @pytest.mark.parametrize(
        "query", ["kuskokwin", "kuskowkim", "kuskokwiim", "kuskokim"]
    )
    def test_one_typo(self, query: str) -> None:
        index = build_index(("TOP OF THE KUSKOKWIM SCHOOL", "NIKOLAI", "AK"))
        assert lines(index.search(query)) == [
            "TOP OF THE KUSKOKWIM SCHOOL, NIKOLAI, AK"
        ]

    def test_typos_only_when_nothing_else_matches(self) -> None:
        index = build_index(
            ("PARK SCHOOL", "MESA", "AZ"), ("PARR SCHOOL", "MESA", "AZ")
        )
        assert lines(index.search("park")) == ["PARK SCHOOL, MESA, AZ"]

    def test_typos_need_four_letters(self) -> None:
        index = build_index(("OAK SCHOOL", "MESA", "AZ"))
        assert index.search("oaj") == []

    def test_two_typos_do_not_match(self) -> None:
        index = build_index(("TOP OF THE KUSKOKWIM SCHOOL", "NIKOLAI", "AK"))
        assert index.search("kuskowkin") == []

    def test_abbreviations_match_both_ways(self) -> None:
        index = build_index(("JEFFERSON ELEM SCHOOL", "BELLEVILLE", "IL"))
        assert len(index.search("jefferson elementary")) == 1
        index = build_index(("JEFFERSON ELEMENTARY SCHOOL", "BELLEVILLE", "IL"))
        assert len(index.search("jefferson elem")) == 1

    def test_spelling_as_written_beats_abbreviation(self) -> None:
        index = build_index(
            ("HIGHLAND PARK ELEM SCH", "BLOOMINGTON", "IN"),
            ("HIGHLAND PARK ELEMENTARY SCHOOL", "PUEBLO", "CO"),
        )
        assert index.search("elementary school highland park")[0].city == "PUEBLO"
        assert index.search("highland park elem sch")[0].city == "BLOOMINGTON"

    def test_state_name_and_postal_code(self) -> None:
        index = build_index(
            ("FOLEY HIGH SCHOOL", "FOLEY", "AL"),
            ("FOLEY HIGH SCHOOL", "FOLEY", "IL"),
        )
        assert index.search("foley high alabama")[0].state == "AL"
        assert index.search("foley high illinois")[0].state == "IL"
        assert index.search("foley high il")[0].state == "IL"

    def test_multi_word_state_name(self) -> None:
        index = build_index(
            ("TREE OF LIFE SCHOOL", "WASHINGTON", "DC"), ("PINE SCHOOL", "MESA", "AZ")
        )
        assert lines(index.search("district of columbia")) == [
            "TREE OF LIFE SCHOOL, WASHINGTON, DC"
        ]

    def test_case_and_punctuation_do_not_matter(self) -> None:
        index = build_index(("TOP OF THE KUSKOKWIM SCHOOL", "NIKOLAI", "AK"))
        assert index.search("Top-of-the KUSKOKWIM!") == index.search(
            "top of the kuskokwim"
        )

    def test_repeated_words_count_once(self) -> None:
        index = build_index(
            ("FOLEY HIGH SCHOOL", "FOLEY", "AL"), ("HIGH POINT SCHOOL", "MESA", "AZ")
        )
        assert index.search("foley foley foley high") == index.search("foley high")

    @pytest.mark.parametrize("query", ["", "   ", "!!!", "zzzzqqq"])
    def test_queries_without_matches(self, query: str) -> None:
        index = build_index(("PINE SCHOOL", "MESA", "AZ"))
        assert index.search(query) == []


class TestRanking:
    def test_rare_words_outweigh_common_ones(self) -> None:
        index = build_index(
            ("ALBERTVILLE HIGH SCHOOL", "ALBERTVILLE", "AL"),
            ("FOLEY MIDDLE SCHOOL", "FOLEY", "AL"),
            ("CENTRAL HIGH SCHOOL", "MESA", "AZ"),
            ("NORTH HIGH SCHOOL", "MESA", "AZ"),
            ("SOUTH HIGH SCHOOL", "MESA", "AZ"),
        )
        assert index.search("foley high")[0].name == "FOLEY MIDDLE SCHOOL"

    def test_more_matching_words_rank_higher(self) -> None:
        index = build_index(
            ("FOLEY MIDDLE SCHOOL", "FOLEY", "AL"),
            ("FOLEY HIGH SCHOOL", "FOLEY", "AL"),
        )
        assert index.search("foley high")[0].name == "FOLEY HIGH SCHOOL"

    def test_name_match_beats_a_school_located_in_the_named_city(self) -> None:
        index = build_index(
            ("LINCOLN ELEMENTARY SCHOOL", "HIGHLAND PARK", "IL"),
            ("HIGHLAND PARK ELEMENTARY SCHOOL", "PUEBLO", "CO"),
        )
        assert index.search("elementary school highland park")[0].city == "PUEBLO"

    @pytest.mark.parametrize(
        ("query", "expected", "other"),
        [
            ("rancho cucamonga middle", "RANCHO CUCAMONGA MIDDLE", "CUCAMONGA MIDDLE"),
            ("cucamonga middle", "CUCAMONGA MIDDLE", "RANCHO CUCAMONGA MIDDLE"),
            (
                "early education center mesa",
                "EARLY EDUCATION CENTER",
                "EAST MESA EARLY CHILDHOOD EDUCATION CENTER",
            ),
        ],
    )
    def test_name_closest_to_the_query_wins(
        self, query: str, expected: str, other: str
    ) -> None:
        city = "MESA" if "mesa" in query else "RANCHO CUCAMONGA"
        index = build_index((other, city, "CA"), (expected, city, "CA"))
        assert index.search(query)[0].name == expected

    def test_partial_word_matches_count_less_in_ties(self) -> None:
        index = build_index(
            ("SOUTHEAST MIDDLE", "SOUTH GATE", "CA"),
            ("SOUTH GATE MIDDLE", "SOUTH GATE", "CA"),
        )
        assert index.search("south gate middle")[0].name == "SOUTH GATE MIDDLE"

    def test_city_breaks_ties_between_same_names(self) -> None:
        index = build_index(
            ("SHERMAN SCHOOL", "FAIRFIELD", "CT"), ("SHERMAN SCHOOL", "SHERMAN", "CT")
        )
        assert index.search("sherman school sherman")[0].city == "SHERMAN"

    def test_identical_results_are_shown_once(self) -> None:
        index = build_index(
            ("SELMA HIGH SCHOOL", "SELMA", "AL"),
            ("SELMA HIGH SCHOOL", "SELMA", "AL"),
            ("SELMA MIDDLE SCHOOL", "SELMA", "AL"),
        )
        assert lines(index.search("selma")) == [
            "SELMA HIGH SCHOOL, SELMA, AL",
            "SELMA MIDDLE SCHOOL, SELMA, AL",
        ]

    def test_order_does_not_depend_on_input_order(self) -> None:
        rows = [
            ("PINE ELEMENTARY", "MESA", "AZ"),
            ("OAK ELEMENTARY", "MESA", "AZ"),
            ("ELM ELEMENTARY", "TEMPE", "AZ"),
            ("ASH ELEMENTARY", "MESA", "AZ"),
        ]
        forward = lines(build_index(*rows).search("elementary mesa", limit=4))
        backward = lines(
            build_index(*reversed(rows)).search("elementary mesa", limit=4)
        )
        assert forward == backward

    def test_limit(self) -> None:
        index = build_index(*[(f"SCHOOL {n}", "MESA", "AZ") for n in range(10)])
        assert len(index.search("school")) == 3
        assert len(index.search("school", limit=1)) == 1
        assert len(index.search("school", limit=20)) == 10
        assert index.search("school", limit=0) == []


def test_format_results() -> None:
    results = [School("1", "FOLEY HIGH SCHOOL", "FOLEY", "AL", "6")]
    assert format_results("foley high", results, 0.0012) == (
        'Results for "foley high" (search took: 0.001s)\n1. FOLEY HIGH SCHOOL\nFOLEY, AL'
    )
    assert format_results("zzz", [], 0) == (
        'Results for "zzz" (search took: 0.000s)\nNo matching schools.'
    )


def test_search_schools_prints_and_returns_results(
    capsys: pytest.CaptureFixture[str],
) -> None:
    index = build_index(
        ("FOLEY HIGH SCHOOL", "FOLEY", "AL"), ("PINE SCHOOL", "MESA", "AZ")
    )
    results = search_schools("foley", index=index)
    assert lines(results) == ["FOLEY HIGH SCHOOL, FOLEY, AL"]
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith('Results for "foley" (search took: ')
    assert out[1:] == ["1. FOLEY HIGH SCHOOL", "FOLEY, AL"]


def test_default_index_is_built_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(school_search, "_default_index", None)
    first = school_search.default_index()
    assert school_search.default_index() is first
    assert len(first.schools) == 34779


# README "Test Cases": the expected schools must be the top hits, in any order.
README_CASES = [
    (
        "elementary school highland park",
        {
            "HIGHLAND PARK ELEMENTARY SCHOOL, MUSCLE SHOALS, AL",
            "HIGHLAND PARK ELEMENTARY SCHOOL, PUEBLO, CO",
        },
    ),
    ("jefferson belleville", {"JEFFERSON ELEM SCHOOL, BELLEVILLE, IL"}),
    ("riverside school 44", {"RIVERSIDE SCHOOL 44, INDIANAPOLIS, IN"}),
    (
        "granada charter school",
        {
            "NORTH VALLEY CHARTER ACADEMY, GRANADA HILLS, CA",
            "GRANADA HILLS CHARTER HIGH, GRANADA HILLS, CA",
        },
    ),
    ("foley high alabama", {"FOLEY HIGH SCHOOL, FOLEY, AL"}),
    ("KUSKOKWIM", {"TOP OF THE KUSKOKWIM SCHOOL, NIKOLAI, AK"}),
]
README_QUERIES = [query for query, _ in README_CASES]


class TestReadmeCases:
    @pytest.mark.parametrize(("query", "expected_top"), README_CASES)
    def test_expected_schools_are_the_top_hits(
        self, bundled_index: SchoolIndex, query: str, expected_top: set[str]
    ) -> None:
        results = bundled_index.search(query)
        assert set(lines(results[: len(expected_top)])) == expected_top

    @pytest.mark.parametrize("query", README_QUERIES[:-1])
    def test_returns_three_results(
        self, bundled_index: SchoolIndex, query: str
    ) -> None:
        assert len(bundled_index.search(query)) == 3

    def test_kuskokwim_returns_a_single_result(
        self, bundled_index: SchoolIndex
    ) -> None:
        assert len(bundled_index.search("KUSKOKWIM")) == 1

    @pytest.mark.parametrize("query", README_QUERIES)
    def test_search_runs_well_under_200ms(
        self, bundled_index: SchoolIndex, query: str
    ) -> None:
        # The README asks for 200ms (10ms for extra credit). These run in 1-4ms
        # on a laptop; 25ms leaves room for slower CI runners while still
        # catching a regression.
        timings = []
        for _ in range(5):
            start = time.perf_counter()
            bundled_index.search(query)
            timings.append(time.perf_counter() - start)
        assert min(timings) < 0.025

    @pytest.mark.parametrize("query", ["school", "elementary", "high school"])
    def test_common_word_queries_run_under_200ms(
        self, bundled_index: SchoolIndex, query: str
    ) -> None:
        start = time.perf_counter()
        bundled_index.search(query)
        assert time.perf_counter() - start < 0.2


class TestProperties:
    @settings(max_examples=300, deadline=None)
    @given(query=st.text(max_size=60), limit=st.integers(min_value=0, max_value=5))
    def test_any_text_returns_at_most_limit_distinct_results(
        self, bundled_index: SchoolIndex, query: str, limit: int
    ) -> None:
        results = bundled_index.search(query, limit)
        assert len(results) <= limit
        assert len(set(lines(results))) == len(results)

    @settings(max_examples=300, deadline=None)
    @given(data=st.data())
    def test_a_school_is_found_by_its_name_city_and_state(
        self, bundled_index: SchoolIndex, data: st.DataObject
    ) -> None:
        # Not always first: "CUCAMONGA MIDDLE RANCHO CUCAMONGA CA" has the same
        # words as the query for RANCHO CUCAMONGA MIDDLE in the same city.
        school = data.draw(st.sampled_from(bundled_index.schools))
        results = bundled_index.search(f"{school.name} {school.city} {school.state}")

        def words(found: School) -> tuple[list[str], list[str], str]:
            return tokenize(found.name), tokenize(found.city), found.state

        assert words(school) in [words(found) for found in results]

    @given(text=st.text())
    def test_tokenize_is_idempotent(self, text: str) -> None:
        tokens = tokenize(text)
        assert tokenize(" ".join(tokens)) == tokens
