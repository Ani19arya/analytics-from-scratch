"""Build the synthetic users and events tables for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/users.csv and data/events.csv.
The data is synthetic and deterministic (fixed seed).
Observation window: signups from January to June 2026, events up to 30 June 2026.
"""
import calendar
import csv
import datetime
import os
import random

random.seed(404)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
LAST_MONTH = 6  # June 2026 is the last month with data


def write(name, rows):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/%s" % (len(rows), name))


def random_day(month):
    days = calendar.monthrange(2026, month)[1]
    return datetime.date(2026, month, random.randint(1, days))


def main():
    os.makedirs(DATA, exist_ok=True)
    users, events = [], []
    uid = 1
    for month in range(1, LAST_MONTH + 1):
        for _ in range(random.randint(40, 65)):
            signup = random_day(month)
            users.append({"user_id": uid, "signup_date": signup.isoformat()})
            # Every user is active on the day they sign up.
            events.append({"user_id": uid, "event_date": signup.isoformat()})
            stay = random.uniform(0.45, 0.8)  # chance of coming back each later month
            for later in range(month + 1, LAST_MONTH + 1):
                if random.random() > stay:
                    break
                # One or two events in an active month, so you must count distinct users.
                for _ in range(random.randint(1, 2)):
                    events.append({"user_id": uid, "event_date": random_day(later).isoformat()})
            uid += 1
    events.sort(key=lambda e: (e["event_date"], e["user_id"]))
    write("users.csv", users)
    write("events.csv", events)


if __name__ == "__main__":
    main()
