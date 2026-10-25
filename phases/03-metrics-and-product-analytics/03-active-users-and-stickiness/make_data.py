"""Build data/events.csv: daily activity for a synthetic workout tracking app,
1 to 30 September 2026.

Columns: user_id, event_date ('YYYY-MM-DD'), event_name.
event_name is app_open (any launch, including taps on a push notification)
or log_workout (the user recorded a workout, the thing the app is for).
At most one row per user, day and event_name. Logging a workout also opens the app.
The data is synthetic and deterministic (fixed seed).
Run from the lesson folder: python3 make_data.py
"""
import csv
import datetime
import os
import random

random.seed(3030)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "events.csv")
START = datetime.date(2026, 9, 1)
# user type: (number of users, chance to open the app on a day, chance to log a workout on a day)
TYPES = [("regular", 20, 0.85, 0.55), ("weekly", 55, 0.28, 0.12), ("drifter", 95, 0.10, 0.01)]


def main():
    rows = []
    user_id = 0
    for _, count, p_open, p_workout in TYPES:
        for _ in range(count):
            user_id += 1
            for offset in range(30):
                day = (START + datetime.timedelta(days=offset)).isoformat()
                workout = random.random() < p_workout
                opened = workout or random.random() < p_open
                if opened:
                    rows.append({"user_id": user_id, "event_date": day, "event_name": "app_open"})
                if workout:
                    rows.append({"user_id": user_id, "event_date": day, "event_name": "log_workout"})
    rows.sort(key=lambda r: (r["event_date"], r["user_id"], r["event_name"]))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["user_id", "event_date", "event_name"])
        w.writeheader()
        w.writerows(rows)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
