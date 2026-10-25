"""Build data/events.csv: raw product events for a synthetic online course shop.

Columns: user_id, event_name, event_time ('YYYY-MM-DD HH:MM:SS').
Funnel steps: view_course, add_to_cart, begin_checkout, purchase.
Users often repeat a step (several views, several checkout attempts).
A small group arrives from a saved cart link: they add to cart without ever
viewing a course page, so they are not in the funnel.
The data is synthetic and deterministic (fixed seed).
Run from the lesson folder: python3 make_data.py
"""
import csv
import datetime
import os
import random

random.seed(202)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "events.csv")
START = datetime.datetime(2026, 10, 1)
STEPS = ["view_course", "add_to_cart", "begin_checkout", "purchase"]
# chance to move on to the next step, given the user reached this one
NEXT = {"view_course": 0.38, "add_to_cart": 0.55, "begin_checkout": 0.42}
# how many times a user fires each event once they reach the step
REPEATS = {"view_course": (1, 6), "add_to_cart": (1, 2), "begin_checkout": (1, 4), "purchase": (1, 1)}


def stamp(t):
    return t.strftime("%Y-%m-%d %H:%M:%S")


def main():
    rows = []
    for user_id in range(1, 421):
        t = START + datetime.timedelta(minutes=random.randint(0, 14 * 24 * 60))
        for step in STEPS:
            for _ in range(random.randint(*REPEATS[step])):
                t += datetime.timedelta(seconds=random.randint(20, 900))
                rows.append({"user_id": user_id, "event_name": step, "event_time": stamp(t)})
            if step == "purchase" or random.random() >= NEXT[step]:
                break
    for user_id in range(421, 436):  # saved cart link: no course view
        t = START + datetime.timedelta(minutes=random.randint(0, 14 * 24 * 60))
        rows.append({"user_id": user_id, "event_name": "add_to_cart", "event_time": stamp(t)})
        if random.random() < 0.6:
            t += datetime.timedelta(seconds=random.randint(20, 900))
            rows.append({"user_id": user_id, "event_name": "begin_checkout", "event_time": stamp(t)})
    rows.sort(key=lambda r: (r["event_time"], r["user_id"]))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["user_id", "event_name", "event_time"])
        w.writeheader()
        w.writerows(rows)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
