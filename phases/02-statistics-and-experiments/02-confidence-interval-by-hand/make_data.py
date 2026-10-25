"""Build the synthetic datasets for lesson 02.

data/orders.csv: 18 order values from a small pilot (synthetic).
data/survey.csv: 400 post-checkout survey answers, 1 = would reorder (synthetic).
Run: python3 make_data.py
"""
import csv
import os
import random

random.seed(202)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def write(path, fieldnames, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print("wrote", len(rows), "rows to", path)


def main():
    os.makedirs(DATA, exist_ok=True)
    orders = [{"order_id": i, "order_value": round(random.gauss(62, 14), 2)}
              for i in range(1, 19)]
    write(os.path.join(DATA, "orders.csv"), ["order_id", "order_value"], orders)
    survey = [{"response_id": i, "would_reorder": 1 if random.random() < 0.31 else 0}
              for i in range(1, 401)]
    write(os.path.join(DATA, "survey.csv"), ["response_id", "would_reorder"], survey)


if __name__ == "__main__":
    main()
