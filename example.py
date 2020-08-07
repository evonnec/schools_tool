import school_search
import time

school_search.search_schools('granada charter school')

start = time.perf_counter_ns()

for i in range(100):
    # school_search.search_schools('granada charter school')
    school_search.search_schools('granada charter school')

end = time.perf_counter_ns()
time_taken = (end - start) / 1000000000
print(time_taken)