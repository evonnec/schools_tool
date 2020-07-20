
#!/usr/bin/env python3

import count_schools

class TestSchoolCount:
    """
    examples for count_schools.py

    >>> count_schools.print_counts()
    Total Schools: 10000
    Schools by State:
    CO: 1000
    DC: 200
    AK: 600
    DE: 300
    AL: 1500
    AR: 1100
    ...
    Schools by Metro-centric locale:
    1: 3000
    3: 2000
    2: 5000
    5: 300
    ...
    City with most schools: CHICAGO (50 schools)
    Unique cities with at least one school: 1000
    """
    def test_total_schools(self):
        self.__init__ = int
        assert total_school_count(get_df()) == 34779
    def test_schools_by_state(self):
        self.__init__ = dict()
        assert len(schools_per_state_count(get_df())) == 21
    def test_schools_by_metro(self):
        self.__init__ = dict()
        assert len(schools_per_metro_count(get_df())) == 9
    def test_schools_by_city(self):
        self.__init__ = dict()
        assert len(schools_per_city_count(get_df())) == 5752

import school_search

class TestSearchSchool:
    """
    Test Cases for school_search.py
    """
    def test_search_highland_park():
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
        assert school_search.search_schools("elementary school highland park")[0] == "HIGHLAND PARK ELEMENTARY SCHOOL: MUSCLE SHOALS, AL"

    def test_search_jefferson_belleville():
        """
        jefferson belleville
        >>> school_search.search_schools("jefferson belleville")
        Results for "jefferson belleville" (search took: 0.000s)
        1. JEFFERSON ELEM SCHOOL
        BELLEVILLE, IL
        2. [Next Best Hit]
        3. [Next Best Hit]
        """
        assert school_search.search_schools("jefferson belleville")[0] == "JEFFERSON ELEM SCHOOL: BELLEVILLE, IL"

    def test_search_riverside():
        """
        riverside school 44
        >>> school_search.search_schools("riverside school 44")
        Results for "riverside school 44" (search took: 0.002s)
        1. RIVERSIDE SCHOOL 44
        INDIANAPOLIS, IN
        2. [Next Best Hit]
        3. [Next Best Hit]
        """
        assert school_search.search_schools("riverside school 44")[0] == "RIVERSIDE SCHOOL 44: INDIANAPOLIS, IN"

    def test_search_granada():
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
        assert school_search.search_schools("granada charter school")[0] == "NORTH VALLEY CHARTER ACADEMY: GRANADA HILLS, CA"

    def test_search_foley_high_alabama():
        """
        foley high alabama
        >>> school_search.search_schools("foley high alabama")
        Results for "foley high alabama" (search took: 0.001s)
        1. FOLEY HIGH SCHOOL
        FOLEY, AL
        2. [Next Best Hit]
        3. [Next Best Hit]
        """
        assert school_search.search_schools("foley high alabama")[0] == "FOLEY HIGH SCHOOL: FOLEY, AL"

    def test_search_kuskokwim():
        """
        KUSKOKWIM
        >>> school_search.search_schools("KUSKOKWIM")
        Results for "KUSKOKWIM" (search took: 0.001s)
        1. TOP OF THE KUSKOKWIM SCHOOL
        NIKOLAI, AK
        (No additional results should be returned)
        """
        assert school_search.search_schools("KUSKOKWIM")[0] == "TOP OF THE KUSKOKWIM SCHOOL: NIKOLAI, AK"