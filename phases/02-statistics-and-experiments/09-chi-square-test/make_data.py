"""Build data/signups.csv for lesson 09 (synthetic).

Lanternway Courses tested three signup flows. Each row is one visitor who
started signing up: user_id, flow (long_form, short_form or magic_link) and
completed (1 if they finished signing up, 0 if they gave up). A blank completed
means the visitor was still on the signup page when the data was pulled, so
the outcome is not known yet.

Visitors were assigned to the three flows at random, one third each. The true
completion rates are 58% (long_form), 66% (short_form) and 62% (magic_link).

Run: python3 make_data.py          (writes data/signups.csv for the default seed)
Use: build(seed) returns {"signups": rows} without writing anything.
"""
import csv
import os
import random

DEFAULT_SEED = 925
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "signups.csv")
FIELDS = ["user_id", "flow", "completed"]
FLOWS = ["long_form", "short_form", "magic_link"]
TRUE_RATE = {"long_form": 0.58, "short_form": 0.66, "magic_link": 0.62}
VISITORS = 1350
STILL_OPEN = 0.01


def build(seed=DEFAULT_SEED, visitors=VISITORS):
    """Return {"signups": rows}. The same seed always gives the same rows."""
    rng = random.Random(seed)
    rows = []
    for user_id in range(1, visitors + 1):
        flow = rng.choice(FLOWS)
        if rng.random() < STILL_OPEN:
            completed = ""
        else:
            completed = 1 if rng.random() < TRUE_RATE[flow] else 0
        rows.append({"user_id": user_id, "flow": flow, "completed": completed})
    return {"signups": rows}


def write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    rows = build()["signups"]
    write_csv(OUT, rows)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
