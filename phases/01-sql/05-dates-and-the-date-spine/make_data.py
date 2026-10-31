"""Build the synthetic signups and report_period tables for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/signups.csv and data/report_period.csv.
The data is synthetic and deterministic (fixed seed).

signups.csv has one row per new user, stamped in UTC, the way the app logs it.
The team reads the report in India time (IST, UTC+5:30), so the export is
padded: it holds every signup from 31 August 2026 00:00 UTC to
1 October 2026 23:59:59 UTC, a little more than September on either side.
report_period.csv is one row: the first and last day of the report, in IST.

The story built into the data: weekdays get more signups than weekends, and a
release on 29 September broke the signup form until 1 October, so 29 and
30 September (IST) have no signups at all.

build(seed) returns the rows without writing anything. The test calls it with
a second seed to check your queries on data you have not seen.
"""
import csv
import datetime
import math
import os
import random

SEED = 505
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
IST = datetime.timedelta(hours=5, minutes=30)
EXPORT_FROM = datetime.datetime(2026, 8, 31, 0, 0, 0)    # UTC
EXPORT_TO = datetime.datetime(2026, 10, 1, 23, 59, 59)   # UTC
OUTAGE = {datetime.date(2026, 9, 29), datetime.date(2026, 9, 30)}  # IST days with the broken form
RATE = {0: 5.0, 1: 5.0, 2: 5.0, 3: 5.0, 4: 5.0, 5: 2.0, 6: 1.5}  # mean signups per IST day, Monday = 0


def poisson(rng, mean):
    """A Poisson count by Knuth's method: how many events land in one day."""
    limit, k, p = math.exp(-mean), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def build(seed=SEED):
    """Return {"signups": [...], "report_period": [...]}, rows as dicts."""
    rng = random.Random(seed)
    stamps = []
    day = datetime.date(2026, 8, 30)  # IST days that can overlap the UTC export
    while day <= datetime.date(2026, 10, 2):
        mean = 0.0 if day in OUTAGE else RATE[day.weekday()]
        for _ in range(poisson(rng, mean)):
            local = datetime.datetime(day.year, day.month, day.day) + datetime.timedelta(seconds=rng.randint(0, 86399))
            utc = local - IST
            if EXPORT_FROM <= utc <= EXPORT_TO:
                stamps.append(utc)
        day += datetime.timedelta(days=1)
    stamps.sort()
    signups = [{"user_id": 7000 + i, "signed_up_at_utc": t.strftime("%Y-%m-%d %H:%M:%S")}
               for i, t in enumerate(stamps, 1)]
    period = [{"start_date": "2026-09-01", "end_date": "2026-09-30"}]
    return {"signups": signups, "report_period": period}


def write(name, rows):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/%s" % (len(rows), name))


def main():
    os.makedirs(DATA, exist_ok=True)
    tables = build()
    write("signups.csv", tables["signups"])
    write("report_period.csv", tables["report_period"])


if __name__ == "__main__":
    main()
