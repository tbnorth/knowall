"""
statspeed.py - test os.stat() speed

Terry N. Brown Brown.TerryN@epa.gov Thu 08/13/2020
"""

import os
import time

TIME_LIMIT = 60  # seconds to spend testing speed
TIME_REPORT = 10  # seconds between reports

time_zero = time.time()
time_last = time_zero

calls_done = 0

for path, dirs, files in os.walk('.'):
    time_now = time.time()
    if time_now - time_zero > TIME_LIMIT:
        break
    if time_now - time_last >= TIME_REPORT:
        time_last = time_now
        rate = calls_done / (time_now - time_zero)
        print(f"{rate} os.stat() calls per second.")
    [os.stat(os.path.join(path, i)) for i in files]
    calls_done += len(files)
rate = calls_done / (time_now - time_zero)
print(f"{rate} os.stat() calls per second.")

