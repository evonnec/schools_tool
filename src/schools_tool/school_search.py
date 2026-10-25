#!/usr/bin/env python3

import csv
import time

_DATAFRAMES: list[list[str]] | None = None


def get_school_data_dataframes(
    state_to_abbreviation_map: dict[str, str],
) -> list[list[str]]:
    """
    Take the csv and return a list of lists dataframe
    """
    global _DATAFRAMES
    if _DATAFRAMES is None:
        input_file = "./input/school_data.csv"
        school_df: list[list[str]] = []
        header = None
        with open(input_file, encoding="iso-8859-1") as schools_input_file:
            csvreader = csv.reader(schools_input_file, delimiter=",")
            for row in csvreader:
                if header is None:
                    header = row
                else:
                    [
                        school_id,
                        agency_id,
                        operating_agency_name,
                        school_name,
                        city_name,
                        state,
                        latitude,
                        longitude,
                        metro_centric_locale,
                        urban_centric_locale,
                        school_status_code,
                    ] = row
                    # if state in state_to_abbreviation_map:
                    #     full_state_name = state_to_abbreviation_map[state]
                    # else:
                    #     full_state_name = ''
                    school_df.append([school_name, city_name, state])
            _DATAFRAMES = school_df
            return school_df
    else:
        return _DATAFRAMES


def map_abbreviation_to_state(
    abbr_file: str = "./input/name-abbr.csv",
) -> dict[str, str]:
    """
    A map of state abbreviations to the state name is needed
    Found a csv from webpage, but libraries not allowed but csv is
    Load the map and return map
    """
    header, map_state = None, dict()
    with open(abbr_file) as map_state_file:
        csvreader = csv.reader(map_state_file, delimiter=",")
        for row in csvreader:
            if header is None:
                header = row
            else:
                [state_name, _, state_code] = row
                map_state.update({state_code.upper(): state_name.upper()})
        return map_state


def is_word_in_dataframe_row(
    dataframe_row: list[str], word: str, state_to_abbreviation_map: dict[str, str]
) -> bool:
    """
    Determine if the search term word is in the dataframe row
    """
    [school_name, city_name, state] = dataframe_row
    if state in state_to_abbreviation_map:
        full_state_name = state_to_abbreviation_map[state]
        search_fields = [school_name, city_name, full_state_name]
    else:
        search_fields = [school_name, city_name]

    is_match = False
    for search_field in search_fields:
        if word.upper() in search_field.upper():
            is_match = True
    return is_match


def search_full_search_term_within_dataframe(
    dataframe: list[list[str]],
    full_search_term: str,
    state_to_abbreviation_map: dict[str, str],
) -> list[list[str]]:
    """
    ranking assigned to school-city-state if all search terms are found, if n - 1 search terms are found, et al.
    this is slower than returning all search terms in school-city-state which was attempted
    """
    words_in_term = full_search_term.split()

    dataframe_scores: dict[int, float] = {}

    for word in words_in_term:
        for index, row in enumerate(dataframe):
            if index not in dataframe_scores:
                dataframe_scores[index] = 0

            if is_word_in_dataframe_row(
                dataframe_row=row,
                word=word,
                state_to_abbreviation_map=state_to_abbreviation_map,
            ):
                # All items are schools, and allowing "school" to give a full
                # score point means we miss great matches.
                # Half a point is arbitrary.
                if word.lower() == "school":
                    dataframe_scores[index] = dataframe_scores[index] + 0.5
                else:
                    dataframe_scores[index] = dataframe_scores[index] + 1

    sorted_schools_by_rank = sorted(
        dataframe_scores.keys(), key=lambda index: dataframe_scores[index], reverse=True
    )
    top_results = [
        dataframe[index] for index in sorted_schools_by_rank if dataframe_scores[index]
    ]
    return top_results


def format_result(dataframe_item: list[str]) -> str:
    """
    Returns a string which looks like README strings
    """
    [school_name, city_name, state] = dataframe_item
    string_to_return = school_name + "\n" + city_name + ", " + state
    return string_to_return


def search_school_results(full_search_term: str) -> list[list[str]]:
    """
    Returns formatted results search_schools
    """
    time_to_make_map_abbrv_start = time.perf_counter_ns()
    state_to_abbreviation_map = map_abbreviation_to_state()
    time_to_make_map_abbrv_end = time.perf_counter_ns()
    time_to_make_map_abbrv = (
        time_to_make_map_abbrv_end - time_to_make_map_abbrv_start
    ) / 1000000000

    time_to_get_dataframes_start = time.perf_counter_ns()
    dataframe_without_headings = get_school_data_dataframes(state_to_abbreviation_map)
    time_to_get_dataframes_end = time.perf_counter_ns()
    time_to_get_dataframes = (
        time_to_get_dataframes_end - time_to_get_dataframes_start
    ) / 1000000000

    time_to_search_start = time.perf_counter_ns()
    search_results = search_full_search_term_within_dataframe(
        full_search_term=full_search_term,
        dataframe=dataframe_without_headings,
        state_to_abbreviation_map=state_to_abbreviation_map,
    )
    time_to_search_end = time.perf_counter_ns()
    time_to_search = (time_to_search_end - time_to_search_start) / 1000000000

    print("time_to_make_map_abbrv", time_to_make_map_abbrv)
    print("time_to_get_dataframes", time_to_get_dataframes)
    print("time_to_search", time_to_search)

    return search_results


def search_schools(full_search_term: str) -> None:
    """
    search_schools function described in README return printed results
    """
    position = 1
    start = time.perf_counter_ns()
    formatted_results = search_school_results(full_search_term)
    end = time.perf_counter_ns()
    execution_time = (end - start) / 1000000000
    print(
        'Results for "'
        + full_search_term
        + '" (search took: '
        + str(execution_time)
        + "s)"
    )
    for search_result in formatted_results[:3]:
        formatted_result = format_result(search_result)
        ready_to_print = str(position) + ". " + formatted_result
        position += 1
        print(ready_to_print)
