#!/usr/bin/env python3

import csv


def get_df(input_file: str = "./input/school_data.csv") -> list[list[str]]:
    """
    Retrieves the csv school_data
    """
    school_df: list[list[str]] = []
    header = None
    with open(input_file, encoding="iso-8859-1") as schools_input_file:
        csvreader = csv.reader(schools_input_file, delimiter=",")
        for row in csvreader:
            if header is None:
                header = row
            else:
                [_, _, _, _, _, _, _, _, _, _, _] = row
                school_df.append(row)
        return school_df


def total_school_count(df: list[list[str]]) -> int:
    """
    Returns total number of schools
    """
    total_schools = set()
    for entry in df:
        [school_id, _, _, _, _, _, _, _, _, _, _] = entry
        total_schools.add(school_id)
    return len(total_schools)


def schools_per_state_count(df: list[list[str]]) -> dict[str, dict[str, int]]:
    """
    Returns dictionary of states and number of schools in each state
    """
    schools_per_state: dict[str, dict[str, int]] = dict()
    for entry in df:
        [_, _, _, _, _, state, _, _, _, _, _] = entry
        if state not in schools_per_state:
            # C should be DC, line 18711, perhaps there should be something to handle this error
            schools_per_state[state] = {"school_count": 1}
        else:
            schools_per_state[state]["school_count"] += 1
    return schools_per_state


def schools_per_metro_count(df: list[list[str]]) -> dict[str, dict[str, int]]:
    """
    Returns number of schools per metro ID
    """
    schools_per_metro: dict[str, dict[str, int]] = dict()
    for entry in df:
        [_, _, _, _, _, _, _, _, metro_centric_locale, _, _] = entry
        if metro_centric_locale not in schools_per_metro:
            # N pertains to AL and FL, 1097 in total -- there ought to be something to handle this
            schools_per_metro[metro_centric_locale] = {"school_count": 1}
        else:
            schools_per_metro[metro_centric_locale]["school_count"] += 1
    return schools_per_metro


def schools_per_city_count(df: list[list[str]]) -> list[tuple[str, dict[str, int]]]:
    """
    Returns number of schools per city in ranked order
    """
    schools_per_city: dict[str, dict[str, int]] = dict()
    for entry in df:
        [_, _, _, _, city_name, state, _, _, _, _, _] = entry
        city = f"{city_name}|{state}".lower()
        if city not in schools_per_city:
            schools_per_city[city] = {"school_count": 1}
        else:
            schools_per_city[city]["school_count"] += 1
    sorted_schools_per_city = sorted(
        schools_per_city.items(), key=lambda x: x[1]["school_count"], reverse=True
    )
    return sorted_schools_per_city


def format_result(dictionary_list: dict[str, dict[str, int]]) -> str:
    """
    Returns a string which looks like README strings
    """
    string_to_return = ""
    for the_key, the_item in dictionary_list.items():
        string_to_return = (
            string_to_return + str(the_key) + " : " + str(the_item) + "\n"
        )

    return string_to_return


def print_counts() -> None:
    print(f"total schools:\n{total_school_count(get_df())}\n")
    print(
        f"schools per state count:\n{format_result(schools_per_state_count(get_df()))}\n"
    )
    print(f"schools per metro:\n{format_result(schools_per_metro_count(get_df()))}\n")
    print(f"city with most schools count:\n{schools_per_city_count(get_df())[0]}\n")
    print(
        f"number of unique cities with one school or more:\n{len(schools_per_city_count(get_df()))}\n"
    )
