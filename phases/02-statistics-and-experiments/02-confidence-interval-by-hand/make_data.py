"""Build the synthetic datasets for lesson 02.

data/orders.csv: the first 18 orders in Harbor Mealkits' new pilot city (synthetic).
data/survey.csv: 400 answers from a random sample of last month's customers,
                 asked after checkout whether they would reorder; 1 = yes (synthetic).

Run: python3 make_data.py          (writes both CSVs for the default seed)
Use: build(seed) returns {"orders": rows, "survey": rows} without writing anything.
"""
import csv
import os
import random

DEFAULT_SEED = 202
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIELDS = {"orders": ["order_id", "order_value"], "survey": ["response_id", "would_reorder"]}


def build(seed=DEFAULT_SEED):
    """Return {"orders": rows, "survey": rows}. The same seed always gives the same rows."""
    rng = random.Random(seed)
    orders = [{"order_id": i, "order_value": round(rng.gauss(62, 14), 2)}
              for i in range(1, 19)]
    survey = [{"response_id": i, "would_reorder": 1 if rng.random() < 0.31 else 0}
              for i in range(1, 401)]
    return {"orders": orders, "survey": survey}


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
