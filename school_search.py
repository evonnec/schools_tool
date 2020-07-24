#!/usr/bin/env python3

import csv
import time 

def get_school_data_dataframes(input_file="./input/school_data.csv"):
    """
    Take the csv and return a list of lists dataframe
    """
    school_df, header = [], None
    with open (input_file, mode='r', encoding='ISO-8859–1') as schools_input_file:
        csvreader = csv.reader(schools_input_file, delimiter=',')    
        for row in csvreader:        
            if header is None: header = row
            else:
                [school_id, agency_id, operating_agency_name, school_name, city_name, state, latitude, longitude, metro_centric_locale, urban_centric_locale, school_status_code] = row
                school_df.append(row)
        return school_df

def map_abbreviation_to_state(abbr_file="./input/name-abbr.csv"):
    """
    A map of state abbreviations to the state name is needed
    Found a csv from webpage, but libraries not allowed but csv is
    Load the map and return map
    """
    header, map_state = None, dict()
    with open(abbr_file, mode='r') as map_state_file:
        csvreader = csv.reader(map_state_file, delimiter = ',')
        for row in csvreader:
            if header is None:
                header = row
            else:
                [state_name, _, state_code] = row
                map_state.update({state_code.upper(): state_name.upper()})
        return map_state

def is_word_in_dataframe_row(dataframe_row, word, state_to_abbreviation_map):
    """
    Determine if the search term word is in the dataframe row 
    """
    [school_id, agency_id, operating_agency_name, school_name, city_name, state, latitude, longitude, metro_centric_locale, urban_centric_locale, school_status_code] = dataframe_row
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


def search_full_search_term_within_dataframe(dataframe, full_search_term, state_to_abbreviation_map):
    """
    ranking assigned to school-city-state if all search terms are found, if n - 1 search terms are found, et al.
    this is slower than returning all search terms in school-city-state which was attempted
    """
    words_in_term = full_search_term.split()

    dataframe_scores = {}

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
                if word.lower() == 'school':
                    dataframe_scores[index] = dataframe_scores[index] + 0.5
                else:
                    dataframe_scores[index] = dataframe_scores[index] + 1

    sorted_schools_by_rank = sorted(dataframe_scores.keys(), key=lambda index: dataframe_scores[index], reverse=True)
    top_results = [dataframe[index] for index in sorted_schools_by_rank if dataframe_scores[index]]
    return top_results

def format_result(dataframe_item):
    """
    Returns a string which looks like README strings
    """
    [school_id, agency_id, operating_agency_name, school_name, city_name, state, latitude, longitude, metro_centric_locale, urban_centric_locale, school_status_code] = dataframe_item
    string_to_return = school_name + '\n' + city_name + ', ' + state
    return string_to_return

def search_school_results(full_search_term):
    """
    Returns formatted results search_schools
    """
    state_to_abbreviation_map = map_abbreviation_to_state()
    dataframe_without_headings = get_school_data_dataframes()
    search_results = search_full_search_term_within_dataframe(
        full_search_term=full_search_term,
        dataframe=dataframe_without_headings,
        state_to_abbreviation_map=state_to_abbreviation_map,
    )
    results = []
    for item in search_results:
        formatted_result = format_result(item)
        results.append(formatted_result)

    return results

def search_schools(full_search_term):
    """
    search_schools function described in README return printed results
    """
    position = 1
    start = time.perf_counter_ns()
    formatted_results = search_school_results(full_search_term)
    end = time.perf_counter_ns()
    execution_time = (end - start) / 1000000000
    print('Results for "' + full_search_term + '" (search took: ' + str(execution_time) + 's)')
    for search_result in formatted_results[:3]:
        ready_to_print = str(position) + '. ' + search_result
        position += 1
        print(ready_to_print)

 
class TestIsWordInDataframeRow:
    """
    Testing different input to return expected
    should accept lowercase and fully spelled terms
    but not other identifiers.
    """
    def test_matches(self):
        iditarod_area_district_data = ['020052000245', '0200520', 'IDITAROD AREA SCHOOL DISTRICT', 'TOP OF THE KUSKOKWIM SCHOOL' , 'NIKOLAI' , 'AK', '63.013100', '-154.373600' , '7' , '43', '1']
        word_and_expected = [
            ('KUSKOKWIM', True),
            ('kuskokwim', True),
            ('Arkansas', True),
            ('arkansas', True),
            ('Nikolai', True),
            ('020052000245', False),
        ]
        for item in word_and_expected:
            word, expected = item
            dataframe_row = iditarod_area_district_data
            state_to_abbreviation_map = {'AL': 'Alabama', 'AK': 'Arkansas'}
            result = is_word_in_dataframe_row(
                dataframe_row=iditarod_area_district_data,
                word=word,
                state_to_abbreviation_map=state_to_abbreviation_map,
            )
            assert result is expected

    def test_state_does_not_exist_in_map(self):
        iditarod_area_district_data = ['020052000245', '0200520', 'IDITAROD AREA SCHOOL DISTRICT', 'TOP OF THE KUSKOKWIM SCHOOL' , 'NIKOLAI' , 'FAKE_STATE', '63.013100', '-154.373600' , '7' , '43', '1']
        word = 'KUSKOKWIM'
        dataframe_row = iditarod_area_district_data
        expected = True
        state_to_abbreviation_map = {'AL': 'Alabama', 'AK': 'Arkansas'}
        result = is_word_in_dataframe_row(
            dataframe_row=iditarod_area_district_data,
            word=word,
            state_to_abbreviation_map=state_to_abbreviation_map,
        )
        assert result is expected


class TestFullSearchTermWithinDataframe:
    """
    tests for function search_full_search_term_within_dataframe
    """
    def test_empty_search_term(self):
        alabama_youth_services_data = ['010000200277', '0100002', 'ALABAMA YOUTH SERVICES' , 'SEQUOYAH SCHOOL - CHALKVILLE CAMPUS', 'PINSON' , 'AL', '33.674697' , '-86.627775' , '3', '41', '1']
        iditarod_area_district_data = ['020052000245', '0200520', 'IDITAROD AREA SCHOOL DISTRICT', 'TOP OF THE KUSKOKWIM SCHOOL' , 'NIKOLAI' , 'AK', '63.013100', '-154.373600' , '7' , '43', '1']
        dataframe = [
            alabama_youth_services_data,
            iditarod_area_district_data,
        ]
        full_search_term = ''
        expected = []
        state_to_abbreviation_map = {'AL': 'Alabama', 'AK': 'Arkansas'}
        result = search_full_search_term_within_dataframe(
            dataframe=dataframe,
            full_search_term=full_search_term,
            state_to_abbreviation_map=state_to_abbreviation_map,
        )
        assert result == expected

    def test_two_words_match(self):
        alabama_youth_services_data = ['010000200277', '0100002', 'ALABAMA YOUTH SERVICES' , 'SEQUOYAH SCHOOL - CHALKVILLE CAMPUS', 'PINSON' , 'AL', '33.674697' , '-86.627775' , '3', '41', '1']
        iditarod_area_district_data = ['020052000245', '0200520', 'IDITAROD AREA SCHOOL DISTRICT', 'TOP OF THE KUSKOKWIM SCHOOL' , 'NIKOLAI' , 'AK', '63.013100', '-154.373600' , '7' , '43', '1']
        dataframe = [
            alabama_youth_services_data,
            iditarod_area_district_data,
        ]
        full_search_term = 'KUSKOKWIM NIKOLAI'
        expected = [iditarod_area_district_data]
        state_to_abbreviation_map = {'AL': 'Alabama', 'AK': 'Arkansas'}
        result = search_full_search_term_within_dataframe(
            dataframe=dataframe,
            full_search_term=full_search_term,
            state_to_abbreviation_map=state_to_abbreviation_map,
        )
        assert result == expected
    
    def test_no_results_for_any_word_in_search_term(self):
        """
        Returns no results at all
        """
        alabama_youth_services_data = ['010000200277', '0100002', 'ALABAMA YOUTH SERVICES' , 'SEQUOYAH SCHOOL - CHALKVILLE CAMPUS', 'PINSON' , 'AL', '33.674697' , '-86.627775' , '3', '41', '1']
        iditarod_area_district_data = ['020052000245', '0200520', 'IDITAROD AREA SCHOOL DISTRICT', 'TOP OF THE KUSKOKWIM SCHOOL' , 'NIKOLAI' , 'AK', '63.013100', '-154.373600' , '7' , '43', '1']
        dataframe = [
            alabama_youth_services_data,
            iditarod_area_district_data,
        ]
        full_search_term = 'FOOBAR BAZBAT'
        expected = []
        state_to_abbreviation_map = {'AL': 'Alabama', 'AK': 'Arkansas'}
        result = search_full_search_term_within_dataframe(
            dataframe=dataframe,
            full_search_term=full_search_term,
            state_to_abbreviation_map=state_to_abbreviation_map,
        )
        assert result == expected
    
    def test_some_search_words_have_no_results(self):
        """
        Returns same as if those were ignored
        """
        alabama_youth_services_data = ['010000200277', '0100002', 'ALABAMA YOUTH SERVICES' , 'SEQUOYAH SCHOOL - CHALKVILLE CAMPUS', 'PINSON' , 'AL', '33.674697' , '-86.627775' , '3', '41', '1']
        iditarod_area_district_data = ['020052000245', '0200520', 'IDITAROD AREA SCHOOL DISTRICT', 'TOP OF THE KUSKOKWIM SCHOOL' , 'NIKOLAI' , 'AK', '63.013100', '-154.373600' , '7' , '43', '1']
        dataframe = [
            alabama_youth_services_data,
            iditarod_area_district_data,
        ]
        full_search_term = 'FOOBAR SEQUOYAH BAZBAT'
        expected = [alabama_youth_services_data]
        state_to_abbreviation_map = {'AL': 'Alabama', 'AK': 'Arkansas'}
        result = search_full_search_term_within_dataframe(
            dataframe=dataframe,
            full_search_term=full_search_term,
            state_to_abbreviation_map=state_to_abbreviation_map,
        )
        assert result == expected

class TestFormatResult:
    """
    Tests if the Format function works as expected
    """
    def test_format_example(self):
        alabama_youth_services_data = ['010000200277', '0100002', 'ALABAMA YOUTH SERVICES' , 'SEQUOYAH SCHOOL - CHALKVILLE CAMPUS', 'PINSON' , 'AL', '33.674697' , '-86.627775' , '3', '41', '1']
        expected = "SEQUOYAH SCHOOL - CHALKVILLE CAMPUS\nPINSON, AL"
        result = format_result(dataframe_item=alabama_youth_services_data)
        assert result == expected

class TestSearchSchool:
    """
    Test Cases for school_search.py
    """

    def test_search_highland_park(self):
        """
        elementary school highland park
        >>> school_search.search_schools("elementary school highland park")
        Results for "elementary school highland park" (search took: 0.009s)
        1. HIGHLAND PARK ELEMENTARY SCHOOL
        MUSCLE SHOALS, AL
        2. HIGHLAND PARK ELEMENTARY SCHOOL
        PUEBLO, CO
        3. [Next Best Hit]
        """
        full_search_term = "elementary school highland park"
        result = search_school_results(full_search_term=full_search_term)
        first_result = result[0]
        second_result = result[1]
        readme_first_result = "HIGHLAND PARK ELEMENTARY SCHOOL\nMUSCLE SHOALS, AL"
        readme_second_result = "HIGHLAND PARK ELEMENTARY SCHOOL\nPUEBLO, CO"
        assert (
            (first_result, second_result) == (readme_first_result, readme_second_result)
            or
            (first_result, second_result) == (readme_second_result, readme_first_result)
        )
        assert len(result) >= 3

    def test_search_jefferson_belleville(self):
        """
        jefferson belleville
        >>> school_search.search_schools("jefferson belleville")
        Results for "jefferson belleville" (search took: 0.000s)
        1. JEFFERSON ELEM SCHOOL
        BELLEVILLE, IL
        2. [Next Best Hit]
        3. [Next Best Hit]
        """
        full_search_term = "jefferson belleville"
        result = search_school_results(full_search_term=full_search_term)
        first_result = result[0]
        readme_first_result = "JEFFERSON ELEM SCHOOL\nBELLEVILLE, IL"
        assert first_result == readme_first_result
        assert len(result) >= 3

    def test_search_riverside(self):
        """
        riverside school 44
        >>> school_search.search_schools("riverside school 44")
        Results for "riverside school 44" (search took: 0.002s)
        1. RIVERSIDE SCHOOL 44
        INDIANAPOLIS, IN
        2. [Next Best Hit]
        3. [Next Best Hit]
        """
        full_search_term = "riverside school 44"
        result = search_school_results(full_search_term=full_search_term)
        first_result = result[0]
        readme_first_result = "RIVERSIDE SCHOOL 44\nINDIANAPOLIS, IN"
        assert first_result == readme_first_result
        assert len(result) >= 3


    def test_search_granada(self):
        """
        granada charter school
        >>> school_search.search_schools("granada charter school")
        Results for "granada charter school" (search took: 0.001s)
        1. NORTH VALLEY CHARTER ACADEMY
        GRANADA HILLS, CA
        2. GRANADA HILLS CHARTER HIGH
        GRANADA HILLS, CA
        3. [Next Best Hit]
        """
        full_search_term = "granada charter school"
        result = search_school_results(full_search_term=full_search_term)
        first_result = result[0]
        second_result = result[1]
        readme_first_result = "NORTH VALLEY CHARTER ACADEMY\nGRANADA HILLS, CA"
        readme_second_result = "GRANADA HILLS CHARTER HIGH\nGRANADA HILLS, CA"
        assert (
            (first_result, second_result) == (readme_first_result, readme_second_result)
            or
            (first_result, second_result) == (readme_second_result, readme_first_result)
        )
        assert len(result) >= 3


    def test_search_foley_high_alabama(self):
        """
        foley high alabama
        >>> school_search.search_schools("foley high alabama")
        Results for "foley high alabama" (search took: 0.001s)
        1. FOLEY HIGH SCHOOL
        FOLEY, AL
        2. [Next Best Hit]
        3. [Next Best Hit]
        """
        full_search_term = "foley high alabama"
        result = search_school_results(full_search_term=full_search_term)
        first_result = result[0]
        readme_first_result = "FOLEY HIGH SCHOOL\nFOLEY, AL"
        assert first_result == readme_first_result
        assert len(result) >= 3

    def test_search_kuskokwim(self):
        """
        KUSKOKWIM
        >>> school_search.search_schools("KUSKOKWIM")
        Results for "KUSKOKWIM" (search took: 0.001s)
        1. TOP OF THE KUSKOKWIM SCHOOL
        NIKOLAI, AK
        (No additional results should be returned)
        """
        full_search_term = "KUSKOKWIM"
        result = search_school_results(full_search_term=full_search_term)
        first_result = result[0]
        readme_first_result = "TOP OF THE KUSKOKWIM SCHOOL\nNIKOLAI, AK"
        assert first_result == readme_first_result
        assert len(result) == 1

