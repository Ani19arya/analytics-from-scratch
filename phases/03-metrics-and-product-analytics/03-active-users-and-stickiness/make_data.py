"""Build data/events.csv: daily activity for a synthetic workout tracking app,
1 to 30 September 2026.

Columns: user_id, event_date ('YYYY-MM-DD'), event_name.
event_name is app_open (any launch of the app) or log_workout (the user recorded
a workout, the thing the app is for). At most one row per user, day and
event_name. Logging a workout also opens the app.
The data is synthetic and deterministic (fixed seed).

    python3 make_data.py          writes data/events.csv (seed 3030)
    import make_data; make_data.build(seed=11)   returns the rows for another seed
"""
import csv
import datetime
import os
import random

SEED = 3030
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "events.csv")
START = datetime.date(2026, 9, 1)
FIELDS = ["user_id", "event_date", "event_name"]
# user type: (number of users, chance to open the app on a day, chance to log a workout on a day)
TYPES = [("regular", 20, 0.85, 0.55), ("weekly", 55, 0.28, 0.12), ("drifter", 95, 0.10, 0.01)]


def build(seed=SEED):
    """Return {"events": [row, ...]}, each row a dict with user_id (int),
    event_date and event_name, sorted as in the CSV."""
    rng = random.Random(seed)
    rows = []
    user_id = 0
    for _, count, p_open, p_workout in TYPES:
        for _ in range(count):
            user_id += 1
            for offset in range(30):
                day = (START + datetime.timedelta(days=offset)).isoformat()
                workout = rng.random() < p_workout
                opened = workout or rng.random() < p_open
                if opened:
                    rows.append({"user_id": user_id, "event_date": day, "event_name": "app_open"})
                if workout:
                    rows.append({"user_id": user_id, "event_date": day, "event_name": "log_workout"})
    rows.sort(key=lambda r: (r["event_date"], r["user_id"], r["event_name"]))
    return {"events": rows}


def write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    rows = build()["events"]
    write_csv(rows, OUT)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
