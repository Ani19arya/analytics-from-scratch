"""Build data/experiment.csv: one row per user in a synthetic checkout A/B test.

variant A is the current checkout page, variant B is the new one.
converted is 1 if the user placed an order. The data is synthetic.
Run: python3 make_data.py
"""
import csv
import os
import random

random.seed(303)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "experiment.csv")
TRUE_RATE = {"A": 0.10, "B": 0.135}


def main():
    rows = []
    for user_id in range(1, 1901):
        variant = "A" if random.random() < 0.5 else "B"
        converted = 1 if random.random() < TRUE_RATE[variant] else 0
        rows.append({"user_id": user_id, "variant": variant, "converted": converted})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["user_id", "variant", "converted"])
        w.writeheader()
        w.writerows(rows)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
