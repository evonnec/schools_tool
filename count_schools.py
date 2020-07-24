#!/usr/bin/env python3

import csv

def get_df(input_file="./input/school_data.csv"):
    """
    Retrieves the csv school_data
    """
    school_df, header = [], None
    with open (input_file, mode='r', encoding='ISO-8859–1') as schools_input_file:
        csvreader = csv.reader(schools_input_file, delimiter=',')    
        for row in csvreader:        
            if header is None: header = row
            else:
                [_, _, _, _, _, _, _, _, _, _, _] = row
                school_df.append(row)
        return school_df

def total_school_count(df):
    """
    Returns total number of schools
    """
    total_schools = set()
    for entry in df:
        [school_id, _, _, _, _, _, _, _, _, _, _] = entry
        total_schools.add(school_id)
    return len(total_schools)

def schools_per_state_count(df):
    """
    Returns dictionary of states and number of schools in each state
    """
    schools_per_state = dict()
    for entry in df:
        [_, _, _, _, _, state, _, _, _, _, _] = entry
        if state not in schools_per_state: 
            # C should be DC, line 18711, perhaps there should be something to handle this error
            schools_per_state[state] = {'school_count': 1}
        else:     
            schools_per_state[state]['school_count'] += 1
    return schools_per_state
    
def schools_per_metro_count(df):
    """
    Returns number of schools per metro ID
    """
    schools_per_metro = dict()
    for entry in df:
        [_, _, _, _, _, _, _, _, metro_centric_locale, _, _] = entry
        if metro_centric_locale not in schools_per_metro: 
            # N pertains to AL and FL, 1097 in total -- there ought to be something to handle this
            schools_per_metro[metro_centric_locale] = {'school_count': 1}
        else:
            schools_per_metro[metro_centric_locale]['school_count'] += 1 
    return schools_per_metro

def schools_per_city_count(df):
    """
    Returns number of schools per city in ranked order
    """
    schools_per_city = dict() 
    for entry in df:
        [_, _, _, _, city_name, state, _, _, _, _, _] = entry
        city = "{0}|{1}".format(city_name, state).lower()                                           
        if city not in schools_per_city: 
            schools_per_city[city] = {'school_count': 1}
        else:
            schools_per_city[city]['school_count'] += 1                                                               
    sorted_schools_per_city = sorted(schools_per_city.items(), key=lambda x: x[1]['school_count'], reverse=True)
    return sorted_schools_per_city

def format_result(dictionary_list):
    """
    Returns a string which looks like README strings
    """
    string_to_return = ""
    for (the_key, the_item) in dictionary_list.items():
        string_to_return = string_to_return + str(the_key) + ' : ' + str(the_item) + '\n'
    
    return string_to_return

def print_counts():
    print("total schools:\n{}\n".format(total_school_count(get_df())))
    print("schools per state count:\n{}\n".format(format_result(schools_per_state_count(get_df())))) #[(k, v) for k, v in schools_per_state_count(get_df()).items()]
    print("schools per metro:\n{}\n".format(format_result(schools_per_metro_count(get_df())))) #[(k, v) for k, v in schools_per_metro_count(get_df()).items()]
    print("city with most schools count:\n{}\n".format(schools_per_city_count(get_df())[0]))
    print("number of unique cities with one school or more:\n{}\n".format(len(schools_per_city_count(get_df()))))

class TestSchoolCount:
    def test_total_schools(self):
        assert total_school_count(get_df()) == 34779
    def test_schools_by_state(self):
        assert len(schools_per_state_count(get_df())) == 21
    def test_schools_by_metro(self):
        assert len(schools_per_metro_count(get_df())) == 9
    def test_schools_by_city(self):
        assert len(schools_per_city_count(get_df())) == 5752