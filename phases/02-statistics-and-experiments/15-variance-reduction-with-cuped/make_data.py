"""Build the synthetic dataset for lesson 15.

Pantrywren, a fictional grocery delivery app, tested a "reorder your
favourites" shelf on its home screen for 14 days. Users were split at random,
one user one group, between control and shelf. The metric is spend per user
during the test, in dollars.

data/users.csv: one row per user in the test:
    user_id        a number
    variant        control or shelf
    pre_spend      the user's spend in the 28 days BEFORE the test started.
                   Blank for users who joined during those 28 days (no history).
    spend          the user's spend during the 14-day test
    test_sessions  app sessions during the test (measured AFTER the split,
                   so the shelf can change it)

How the data is built (the test does not rely on this, it recomputes
everything): each user has a steady appetite for groceries that drives both
pre_spend and spend, so the two are strongly correlated. The shelf adds a few
dollars of spend and also makes users open the app more often.

Run: python3 make_data.py      (writes data/users.csv for the default seed)
Use: build(seed) returns {"users": rows} without writing anything.
"""
import csv
import math
import os
import random

DEFAULT_SEED = 1644
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIELDS = {"users": ["user_id", "variant", "pre_spend", "spend", "test_sessions"]}
USERS = 1800
NEW_SHARE = 0.12
LIFT = 4.0


def build(seed=DEFAULT_SEED):
    """Return {"users": rows}. The same seed always gives the same rows."""
    rng = random.Random(seed)
    rows = []
    for i in range(1, USERS + 1):
        variant = "shelf" if rng.random() < 0.5 else "control"
        appetite = rng.lognormvariate(math.log(45), 0.6)
        new_user = rng.random() < NEW_SHARE
        pre = None if new_user else max(0.0, appetite * 2 * rng.lognormvariate(0, 0.25) - 5)
        spend = max(0.0, appetite * rng.lognormvariate(0, 0.28) + rng.gauss(0, 5))
        if rng.random() < 0.05:
            spend = 0.0
        sessions = 1 + int(spend / 12 + rng.expovariate(0.4))
        if variant == "shelf":
            if spend > 0:
                spend += rng.gauss(LIFT, 3)
            sessions += 2 + int(rng.expovariate(0.5))
        rows.append({"user_id": 80000 + i, "variant": variant,
                     "pre_spend": "" if pre is None else "%.2f" % pre,
                     "spend": "%.2f" % max(0.0, spend), "test_sessions": sessions})
    return {"users": rows}


def write_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_all(folder, tables):
    for name, rows in tables.items():
        write_csv(os.path.join(folder, name + ".csv"), rows, FIELDS[name])


def main():
    tables = build()
    write_all(DATA, tables)
    for name, rows in tables.items():
        print("wrote", len(rows), "rows to", os.path.join(DATA, name + ".csv"), "(synthetic)")


if __name__ == "__main__":
    main()
