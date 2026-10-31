"""Build data/visitors.csv: the 200 visitors who landed on Tidewater Outdoor's new
gear guide page on 27 October 2026, and whether each one bought (synthetic).

The data is synthetic. Each visitor buys with a hidden rate set below. The lesson
never uses it, just as a real analyst would never know it.

Run: python3 make_data.py          (writes data/visitors.csv for the default seed)
Use: build(seed) returns {"visitors": [row dicts]} without writing anything.
"""
import csv
import os
import random

DEFAULT_SEED = 507
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "visitors.csv")
FIELDS = ["visitor_id", "visit_date", "bought"]
VISITORS = 200
HIDDEN_RATE = 0.13


def build(seed=DEFAULT_SEED):
    """Return {"visitors": rows}. The same seed always gives the same rows."""
    rng = random.Random(seed)
    rows = []
    for i in range(1, VISITORS + 1):
        rows.append({"visitor_id": i, "visit_date": "2026-10-27",
                     "bought": 1 if rng.random() < HIDDEN_RATE else 0})
    return {"visitors": rows}


def write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    rows = build()["visitors"]
    write_csv(OUT, rows)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
