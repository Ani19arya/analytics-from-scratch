"""Build the synthetic users and events tables for this lesson.

Run from the lesson folder: python3 make_data.py
Writes two files to data/:
  users.csv   one row per account: platform, country, and is_internal (1 for
              staff and test accounts)
  events.csv  one row per logged event in September and October 2026:
              app_open, workout_logged, or push_received (a notification the
              app SENT; the user did nothing). A few app_open events come from
              devices that never signed in, so their user_id is blank.
The data is synthetic and deterministic (fixed seed).

The test calls build(seed=...) with another seed to get a second,
different dataset in memory, so code that hard-codes the answers fails.
"""
import csv
import datetime
import os
import random

DEFAULT_SEED = 409

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIRST, LAST = datetime.date(2026, 9, 1), datetime.date(2026, 10, 31)


def build(seed=DEFAULT_SEED):
    """Return {"users": [...], "events": [...]} with values as they appear in the CSV files."""
    rng = random.Random(seed)
    users = []
    for n in range(1, 241):
        users.append({"user_id": n, "platform": rng.choice(["android", "android", "ios"]),
                      "country": rng.choice(["IN", "IN", "IN", "AE", "GB"]),
                      "is_internal": 1 if n % 30 == 0 else 0})
    events, event_id = [], 0
    n_days = (LAST - FIRST).days + 1
    for user in users:
        kind = rng.random()
        if user["is_internal"]:
            engagement = 0.5          # staff open the app to test it
        elif kind < 0.35:
            engagement = 0.0          # signed up, never came back: only pushes reach them
        elif kind < 0.7:
            engagement = 0.08
        else:
            engagement = 0.25
        for offset in sorted(rng.sample(range(n_days), rng.randint(1, 4))):
            if rng.random() < 0.8:
                event_id += 1
                events.append({"event_id": event_id, "user_id": user["user_id"],
                               "event_date": (FIRST + datetime.timedelta(days=offset)).isoformat(),
                               "event_type": "push_received"})
        if engagement:
            for offset in range(n_days):
                if rng.random() < engagement * 0.3:
                    day = (FIRST + datetime.timedelta(days=offset)).isoformat()
                    for event_type in ["app_open"] + (["workout_logged"] if rng.random() < 0.6 else []):
                        event_id += 1
                        events.append({"event_id": event_id, "user_id": user["user_id"], "event_date": day,
                                       "event_type": event_type})
    for _ in range(12):
        event_id += 1
        events.append({"event_id": event_id, "user_id": "",
                       "event_date": (FIRST + datetime.timedelta(days=rng.randrange(n_days))).isoformat(),
                       "event_type": "app_open"})
    events.sort(key=lambda e: (e["event_date"], e["event_id"]))
    return {"users": users, "events": events}


def main():
    os.makedirs(DATA, exist_ok=True)
    for name, rows in build().items():
        with open(os.path.join(DATA, name + ".csv"), "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print("wrote %d rows to data/%s.csv" % (len(rows), name))


if __name__ == "__main__":
    main()
