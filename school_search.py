#!/usr/bin/env python3

import csv
import time 
import itertools

def get_df_ss(input_file="./input/school_data.csv"):
    school_df, header = [], None
    with open (input_file, mode='r', encoding='ISO-8859–1') as schools_input_file:
        csvreader = csv.reader(schools_input_file, delimiter=',')    
        for row in csvreader:        
            if header is None: header = row
            else:
                [school_id, agency_id, operating_agency_name, school_name, city_name, state, latitude, longitude, metro_centric_locale, urban_centric_locale, school_status_code] = row
                school_df.append(row)
        return school_df

def map_state_to_abbr(abbr_file="./input/name-abbr.csv"):
    header, map_state = None, dict()
    with open(abbr_file, mode='r') as map_state_file:
        csvreader = csv.reader(map_state_file, delimiter = ',')
        for row in csvreader:
            if header is None:
                header = row
            else:
                [state_name, abbr, state_code] = row
                map_state.update({state_name.upper() : state_code.upper()})
        return map_state

# Create a class or tuple and load the data in the class
# Let it be a hashmap / dictionary
# search using keywords for each of the fields
# if int, search int columns, if string, search string columns
# test cases look for school name or city fields

def make_existing_terms(df, state_map, s):
    terms, existing_terms, ranking, counted = s.split(), dict(), {}, {}

    for line in df:
        [_, _, _, school_name, city_name, state, _, _, _, _, _] = line
        school_terms, city_terms = school_name.split(), city_name.split()
        search_terms = set(school_terms + city_terms)
        
        for term in terms:
            if term.upper() not in search_terms:
                continue

            if term.upper() not in counted and term.upper() in search_terms:
                counted[term.upper()] = {'term_count': 1}
            elif term.upper() in search_terms:
                counted[term.upper()]['term_count'] += 1

            if state_map.get(term.upper()):
                value = state_map.get(term.upper())
                if value in existing_terms and value.upper() == state.upper():
                    existing_terms[value].add((school_name, city_name, state))
                elif value.upper() == state.upper():
                    existing_terms[value] = {(school_name, city_name, state)}

            if term.upper() in search_terms:
                if term.upper() in existing_terms:
                    existing_terms[term.upper()].add((school_name, city_name, state))
                else:
                    existing_terms[term.upper()] = {(school_name, city_name, state)}
    print(counted)
    existing_terms_adj = {key: value for key, value in existing_terms.items() if len(existing_terms[key]) < 50}
    
    # set_existing_terms = set.intersection(*(set(val) for val in existing_terms.values()))
    return existing_terms_adj # set_existing_terms

    #       for i in hit:
    #           if i not in ranking: ranking[i] = {'count': 0}
    #           ranking[i]['count'] += 1
    #       sorted_hits = sorted(ranking.items(), key=lambda x: x[1]['count'], reverse=True)

# {'FOLEY': {('MAGNOLIA SCHOOL', 'FOLEY', 'AL'), ('FOLEY INTERMEDIATE SCHOOL', 'FOLEY', 'AL'), ('FOLEY HIGH SCHOOL', 'FOLEY', 'AL'), ('FOLEY MIDDLE SCHOOL', 'FOLEY', 'AL'), ('FOLEY ELEMENTARY SCHOOL', 'FOLEY', 'AL')}}

def search_schools(s):
    start = time.perf_counter_ns()
    existing_terms = make_existing_terms(get_df_ss(), map_state_to_abbr(), s)
    ranking, terms = {}, s.split()
    
    counter = itertools.count(start=0,step=1)

    for k, v in existing_terms.items():
        if all(value for key, value in existing_terms.items() if all(terms) in value):
            # print(all(item for key, value in existing_terms.items() if all(terms) in item))
            for item in v:
                ideal_hit = set.intersection(*(set(item) for item in existing_terms.values()))
            ranking.update(counter.next(), v)

    end = perf_counter_ns()
    execution_time = (end - start)
    return ranking, ideal_hit, ranking.keys(), execution_time
 

class TestSearchSchool:
    """
    Test Cases for school_search.py
    """
    def test_search_highland_park(self):
        self.search_school = "elementary school highland park"
        assert search_schools("elementary school highland park")[0] == "HIGHLAND PARK ELEMENTARY SCHOOL MUSCLE SHOALS, AL"

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
        self.search_school = "jefferson belleville"
        assert search_schools("jefferson belleville")[0] == "JEFFERSON ELEM SCHOOL: BELLEVILLE, IL"

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
        self.search_school = "riverside school 44"
        assert search_schools("riverside school 44")[0] == "RIVERSIDE SCHOOL 44: INDIANAPOLIS, IN"

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
        self.search_school = "granada charter school"
        assert search_schools("granada charter school")[0] == "NORTH VALLEY CHARTER ACADEMY: GRANADA HILLS, CA"

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
        self.search_school = "foley high alabama"
        assert search_schools("foley high alabama")[0] == "FOLEY HIGH SCHOOL: FOLEY, AL"

    def test_search_kuskokwim(self):
        """
        KUSKOKWIM
        >>> school_search.search_schools("KUSKOKWIM")
        Results for "KUSKOKWIM" (search took: 0.001s)
        1. TOP OF THE KUSKOKWIM SCHOOL
        NIKOLAI, AK
        (No additional results should be returned)
        """
        self.search_school = "KUSKOKWIM"
        assert search_schools("KUSKOKWIM")[0] == "TOP OF THE KUSKOKWIM SCHOOL: NIKOLAI, AK"

def main(s):
    TestSearchSchool.test_search_foley_high_alabama("foley high alabama")
    TestSearchSchool.test_search_granada("granada charter school")
    TestSearchSchool.test_search_highland_park("elementary school highland park")
    TestSearchSchool.test_search_jefferson_belleville("jefferson belleville")
    TestSearchSchool.test_search_kuskokwim("KUSKOKWIM")
    TestSearchSchool.test_search_riverside("riverside school 44")
    # get_df()
    dict_make_existing_terms(get_df_ss(), map_state_to_abbr(), s)
    search_schools(s)

if __name__ == "__main__":
    main(str)

# class SchoolSearch:
#     def __init__(self, name, city, metro, urban):
#         self.data = {}
#         self.name = name
#         self.city = city_name
#         self.state = state
        
#     # def sort(self, data):
#     #     sorted(self.data.items(), key=lambda x: x[1], reverse=True)

#     def find(self, data):
#         self.data.find
        
#     def add(self, item, priority):
#         self.data.update({item: priority})
        
#     def pop(self, item):
#         self.data.popitem()
