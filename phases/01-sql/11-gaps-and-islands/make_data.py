"""Build the synthetic workout logs for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/workouts.csv.
The data is synthetic and deterministic (fixed seed). October 2026, one row
per logged workout, times to the second in the user's local time.

The story built into the data: Fitloop users work out in runs of days, then
skip a day or a few. Some log two workouts on one day (a morning run and an
evening yoga class), and the app sometimes sends the same workout twice a few
seconds apart. A few rows arrived with no time at all after a sync error.

build(seed) returns the rows without writing anything. The test calls it with
a second seed to check your queries on data you have not seen.
"""
import csv
import datetime
import os
import random

SEED = 1111
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIRST_DAY = datetime.date(2026, 10, 1)
DAYS = 31
TYPES = ["run", "run", "walk", "cycle", "yoga", "strength", "strength", "swim"]


def build(seed=SEED):
    """Return {"workouts": [...]}, rows as dicts."""
    rng = random.Random(seed)
    raw = []
    for u in range(1, 51):
        uid = "F%03d" % u
        keep_going = rng.choice([0.35, 0.55, 0.7, 0.8, 0.9])   # chance to work out again the day after a workout
        restart = rng.choice([0.15, 0.3, 0.45])                # chance to work out the day after a rest day
        active = rng.random() < restart
        for i in range(DAYS):
            day = FIRST_DAY + datetime.timedelta(days=i)
            if active:
                n = 2 if rng.random() < 0.12 else 1             # two workouts on one day
                for _ in range(n):
                    t = datetime.datetime(day.year, day.month, day.day, rng.randint(5, 22), rng.randint(0, 59),
                                          rng.randint(0, 59))
                    kind, minutes = rng.choice(TYPES), rng.randint(15, 75)
                    raw.append((t, uid, kind, minutes))
                    if rng.random() < 0.04:                     # the app sent the same workout twice
                        raw.append((t + datetime.timedelta(seconds=rng.randint(1, 9)), uid, kind, minutes))
            active = rng.random() < (keep_going if active else restart)
    raw.sort()
    rows = []
    for n, (t, uid, kind, minutes) in enumerate(raw, 1):
        stamp = t.strftime("%Y-%m-%d %H:%M:%S")
        if rng.random() < 0.005:
            stamp = None                                        # sync error: no time
        rows.append({"workout_id": n, "user_id": uid, "logged_at": stamp, "workout_type": kind, "minutes": minutes})
    return {"workouts": rows}


def write(name, rows):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/%s" % (len(rows), name))


def main():
    os.makedirs(DATA, exist_ok=True)
    write("workouts.csv", build()["workouts"])


if __name__ == "__main__":
    main()
