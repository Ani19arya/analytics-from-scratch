"""Build the synthetic revenue by product line table for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/product_line_revenue.csv: one row per product line.
The data is synthetic and deterministic (fixed seed).

The test calls build(seed=...) with another seed to get a second,
different dataset in memory, so code that hard-codes the answers fails.
"""
import csv
import os
import random

DEFAULT_SEED = 404

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
LINES = ["Road", "Mountain", "Gravel", "Kids", "Parts & Accessories", "Service"]


def build(seed=DEFAULT_SEED):
    """Return {"product_line_revenue": [row, ...]} with revenue as an integer."""
    rng = random.Random(seed)
    return {"product_line_revenue": [{"product_line": line, "revenue": rng.randint(40, 480) * 100} for line in LINES]}


def main():
    os.makedirs(DATA, exist_ok=True)
    rows = build()["product_line_revenue"]
    with open(os.path.join(DATA, "product_line_revenue.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["product_line", "revenue"])
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/product_line_revenue.csv" % len(rows))


if __name__ == "__main__":
    main()
