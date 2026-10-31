"""Build the synthetic datasets for lesson 07.

data/population.csv: every one of the 1,200 September 2026 orders in Harbor
                     Mealkits' home city (synthetic). The lesson treats it as a
                     population we know completely.
data/weeks.csv:      the first 18 orders of two weeks in the new pilot city,
                     36 rows (synthetic).

Order values come from the same mix in both files: most orders are a regular box
for two, about 12% are big family or party boxes. That gives a long right tail.

Run: python3 make_data.py          (writes both CSVs for the default seed)
Use: build(seed) returns {"population": rows, "weeks": rows} without writing anything.
"""
import csv
import math
import os
import random

DEFAULT_SEED = 2022
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIELDS = {"population": ["order_id", "order_value"],
          "weeks": ["week_start", "order_id", "order_value"]}
POPULATION = 1200
PER_WEEK = 18
WEEKS = ["2026-10-12", "2026-10-19"]


def order_value(rng):
    if rng.random() < 0.12:
        return round(rng.lognormvariate(math.log(110), 0.30), 2)
    return round(rng.lognormvariate(math.log(48), 0.28), 2)


def build(seed=DEFAULT_SEED):
    """Return {"population": rows, "weeks": rows}. The same seed always gives the same rows."""
    rng = random.Random(seed)
    population = [{"order_id": i, "order_value": order_value(rng)} for i in range(1, POPULATION + 1)]
    weeks = []
    next_id = 1
    for week in WEEKS:
        for _ in range(PER_WEEK):
            weeks.append({"week_start": week, "order_id": next_id, "order_value": order_value(rng)})
            next_id += 1
    return {"population": population, "weeks": weeks}


def write_csv(path, fieldnames, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def write_all(folder, tables):
    for name, rows in tables.items():
        write_csv(os.path.join(folder, name + ".csv"), FIELDS[name], rows)


def main():
    tables = build()
    write_all(DATA, tables)
    for name, rows in tables.items():
        print("wrote", len(rows), "rows to", os.path.join(DATA, name + ".csv"))


if __name__ == "__main__":
    main()
