"""Build data/experiment.csv: one row per user in a synthetic checkout A/B test.

variant A is the current checkout page, variant B is the new one.
converted is 1 if the user placed an order. The data is synthetic: users are
split 50/50 at random, and the true conversion rates are 10% for A and 13.5% for B.

Run: python3 make_data.py          (writes data/experiment.csv for the default seed)
Use: build(seed) returns {"experiment": rows} without writing anything.
"""
import csv
import os
import random

DEFAULT_SEED = 303
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "experiment.csv")
TRUE_RATE = {"A": 0.10, "B": 0.135}
FIELDS = ["user_id", "variant", "converted"]


def build(seed=DEFAULT_SEED, users=1900):
    """Return {"experiment": rows}. The same seed always gives the same rows."""
    rng = random.Random(seed)
    rows = []
    for user_id in range(1, users + 1):
        variant = "A" if rng.random() < 0.5 else "B"
        converted = 1 if rng.random() < TRUE_RATE[variant] else 0
        rows.append({"user_id": user_id, "variant": variant, "converted": converted})
    return {"experiment": rows}


def write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    rows = build()["experiment"]
    write_csv(OUT, rows)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
