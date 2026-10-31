"""Build data/events.csv: raw product events for a synthetic online course shop.

Columns: user_id, event_name, event_time ('YYYY-MM-DD HH:MM:SS').
Funnel steps: view_course, add_to_cart, begin_checkout, purchase.
Users often repeat a step (several views, several checkout attempts).
A small group arrives from a saved cart link: they add to cart without ever
viewing a course page, so they are not in the funnel.
The data is synthetic and deterministic (fixed seed).

    python3 make_data.py          writes data/events.csv (seed 202)
    import make_data; make_data.build(seed=5)   returns the rows for another seed
"""
import csv
import datetime
import os
import random

SEED = 202
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "events.csv")
START = datetime.datetime(2026, 10, 1)
STEPS = ["view_course", "add_to_cart", "begin_checkout", "purchase"]
FIELDS = ["user_id", "event_name", "event_time"]
# chance to move on to the next step, given the user reached this one
NEXT = {"view_course": 0.38, "add_to_cart": 0.55, "begin_checkout": 0.42}
# how many times a user fires each event once they reach the step
REPEATS = {"view_course": (1, 6), "add_to_cart": (1, 2), "begin_checkout": (1, 4), "purchase": (1, 1)}


def stamp(t):
    return t.strftime("%Y-%m-%d %H:%M:%S")


def build(seed=SEED):
    """Return {"events": [row, ...]}, each row a dict with user_id (int),
    event_name and event_time (text), sorted by time as in the CSV."""
    rng = random.Random(seed)
    rows = []
    for user_id in range(1, 421):
        t = START + datetime.timedelta(minutes=rng.randint(0, 14 * 24 * 60))
        for step in STEPS:
            for _ in range(rng.randint(*REPEATS[step])):
                t += datetime.timedelta(seconds=rng.randint(20, 900))
                rows.append({"user_id": user_id, "event_name": step, "event_time": stamp(t)})
            if step == "purchase" or rng.random() >= NEXT[step]:
                break
    for user_id in range(421, 436):  # saved cart link: no course view
        t = START + datetime.timedelta(minutes=rng.randint(0, 14 * 24 * 60))
        rows.append({"user_id": user_id, "event_name": "add_to_cart", "event_time": stamp(t)})
        if rng.random() < 0.6:
            t += datetime.timedelta(seconds=rng.randint(20, 900))
            rows.append({"user_id": user_id, "event_name": "begin_checkout", "event_time": stamp(t)})
    rows.sort(key=lambda r: (r["event_time"], r["user_id"]))
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
