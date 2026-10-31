"""Build the synthetic users and events tables for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/users.csv and data/events.csv.
The data is synthetic and deterministic (fixed seed).
Observation window: signups from January to June 2026, events up to 30 June 2026.

build(seed) returns the rows without writing anything. The test calls it with
a second seed to check your queries on data you have not seen.
"""
import calendar
import csv
import datetime
import os
import random

SEED = 404
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
LAST_MONTH = 6  # June 2026 is the last month with data


def random_day(rng, month):
    days = calendar.monthrange(2026, month)[1]
    return datetime.date(2026, month, rng.randint(1, days))


def build(seed=SEED):
    """Return {"users": [...], "events": [...]}, rows as dicts."""
    rng = random.Random(seed)
    users, events = [], []
    uid = 1
    for month in range(1, LAST_MONTH + 1):
        for _ in range(rng.randint(40, 65)):
            signup = random_day(rng, month)
            users.append({"user_id": uid, "signup_date": signup.isoformat()})
            # Every user is active on the day they sign up.
            events.append({"user_id": uid, "event_date": signup.isoformat()})
            stay = rng.uniform(0.45, 0.8)  # chance of coming back each later month
            for later in range(month + 1, LAST_MONTH + 1):
                if rng.random() > stay:
                    break
                # One or two events in an active month, so you must count distinct users.
                for _ in range(rng.randint(1, 2)):
                    events.append({"user_id": uid, "event_date": random_day(rng, later).isoformat()})
            uid += 1
    events.sort(key=lambda e: (e["event_date"], e["user_id"]))
    return {"users": users, "events": events}


def write(name, rows):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/%s" % (len(rows), name))


def main():
    os.makedirs(DATA, exist_ok=True)
    tables = build()
    write("users.csv", tables["users"])
    write("events.csv", tables["events"])


if __name__ == "__main__":
    main()
