"""Build data/members.csv for lesson 11 (synthetic).

Larkspur Coffee, a fictional coffee chain, runs a loyalty app. One row per
loyalty member over the last 30 days:

member_id   a made-up id
visits_30d  paid visits in 30 days
spend_30d   total spend in dollars in 30 days; blank when the member's spend
            failed to sync from the till, so it is unknown

How the data is made: visits are right-skewed (most members come a few times,
some nearly every day). Spend is a base of 6 dollars plus 4.60 dollars per
visit, plus random noise with a standard deviation of 9 dollars, so the true
line is spend = 6 + 4.6 * visits. Spend never goes below 0.

Run: python3 make_data.py          (writes data/members.csv for the default seed)
Use: build(seed) returns {"members": rows} without writing anything.
"""
import csv
import math
import os
import random

DEFAULT_SEED = 1111
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "members.csv")
FIELDS = ["member_id", "visits_30d", "spend_30d"]
MEMBERS = 420
BASE, PER_VISIT, NOISE = 6.0, 4.6, 9.0
SYNC_FAILED = 0.015


def build(seed=DEFAULT_SEED):
    """Return {"members": rows}. The same seed always gives the same rows."""
    rng = random.Random(seed)
    rows = []
    for i in range(1, MEMBERS + 1):
        visits = min(28, max(1, round(rng.lognormvariate(math.log(7), 0.55))))
        spend = max(0.0, BASE + PER_VISIT * visits + rng.gauss(0, NOISE))
        value = "" if rng.random() < SYNC_FAILED else "%.2f" % spend
        rows.append({"member_id": 20000 + i, "visits_30d": visits, "spend_30d": value})
    return {"members": rows}


def write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    rows = build()["members"]
    write_csv(OUT, rows)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
