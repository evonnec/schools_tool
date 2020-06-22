#!/usr/bin/env python3

import csv

input_file = "./input/school_data.csv"

header = None
total_schools = set()                       # count unique schools
schools_per_state = dict()                  # state: school_count
schools_per_metro = dict()                  # metro-centric locale: school_count
city_with_most_schools = dict()             # unique_city: school_count -- ordered or find max count per city
                                            # unique_city: city_count -- where school_count not NULL

with open (input_file, mode='r', encoding='ISO-8859–1') as schools_input_file:
    csvreader = csv.reader(schools_input_file, delimiter=',')    
    for row in csvreader:        
        if header is None:
            header = row
        else:
            [school_id, agency_id, operating_agency_name, school_name, city_name, state, latitude, longitude, metro_centric_locale, urban_centric_locale, school_status_code] = row
            city = "{0}|{1}".format(city_name, state).lower()                                                               # define city key; latitude/longitude fields are incomplete
            total_schools.add(school_id)                                                                                    # count unique schools
            if state not in schools_per_state: schools_per_state[state] = {'school_count': 0}                               # initialize state: school_count
            if metro_centric_locale not in schools_per_metro: schools_per_metro[metro_centric_locale] = {'school_count': 0} # initialize metro: school_count
            if city not in city_with_most_schools: city_with_most_schools[city] = {'school_count': 0}                       # initialize city: school_count
            schools_per_state[state]['school_count'] += 1                                                                   # do the count for by state
            schools_per_metro[metro_centric_locale]['school_count'] += 1                                                    # do the count for by metro
            city_with_most_schools[city]['school_count'] += 1                                                               # do the count for by city
    sorted_city_with_most_schools = sorted(city_with_most_schools.items(), key=lambda x: x[1]['school_count'], reverse=True)# sort city descending

    def print_counts():
        print("total schools: {}\n".format(len(total_schools)))
        print("schools per state count: {}\n".format([(k, v) for k, v in schools_per_state.items()]))
        print("schools per metro: {}\n".format([(k, v) for k, v in schools_per_metro.items()]))
        print("city with most schools count: {}\n".format(sorted_city_with_most_schools[0]))
        print("number of unique cities with one school or more: {}\n".format(len(city_with_most_schools)))