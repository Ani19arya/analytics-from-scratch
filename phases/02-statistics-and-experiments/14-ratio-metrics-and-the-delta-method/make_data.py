"""Build the synthetic dataset for lesson 14.

Cobblewick, a fictional job board, tested a "quick apply" button. Job seekers
were split at random, one user one group, between control (the current apply
form) and quick_apply. The metric is replies per application: employer replies
divided by applications sent.

data/users.csv: one row per job seeker in the test:
    user_id       a number
    variant       control or quick_apply
    applications  applications the user sent during the test (0 if none)
    replies       employer replies to those applications

How the data is built (the test does not rely on this, it recomputes everything):
some users send many applications and most of those get no reply, so one
user's applications are alike and a few heavy users carry a large share of
each total. Quick apply makes users send more applications and lowers the
reply chance slightly.

Run: python3 make_data.py      (writes data/users.csv for the default seed)
Use: build(seed) returns {"users": rows} without writing anything.
"""
import csv
import math
import os
import random

DEFAULT_SEED = 1561
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIELDS = {"users": ["user_id", "variant", "applications", "replies"]}
USERS = 1600


def build(seed=DEFAULT_SEED):
    """Return {"users": rows}. The same seed always gives the same rows."""
    rng = random.Random(seed)
    rows = []
    for i in range(1, USERS + 1):
        variant = "quick_apply" if rng.random() < 0.5 else "control"
        if rng.random() < 0.12:
            apps = 0
        else:
            heavy = rng.random() < 0.15
            apps = 1 + int(rng.expovariate(1 / (25.0 if heavy else 4.0)))
            if variant == "quick_apply":
                apps = int(round(apps * 1.25))
            apps = min(apps, 150)
        quality = rng.betavariate(0.8, 4)
        reply_p = quality / (1 + math.log(1 + apps) / 2)
        if variant == "quick_apply":
            reply_p *= 0.96
        replies = sum(1 for _ in range(apps) if rng.random() < reply_p)
        rows.append({"user_id": 50000 + i, "variant": variant,
                     "applications": apps, "replies": replies})
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
