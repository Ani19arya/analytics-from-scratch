"""Build the synthetic sales table for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/sales.csv: one row per order line, January to June 2026, with the
region (Alpine, Coast, Lakes) and the product category. Sales grow through the
spring and differ by region, so ranks and shares move.
The data is synthetic and deterministic (fixed seed).

The test calls build(seed=...) with another seed to get a second,
different dataset in memory, so a query that hard-codes the answers fails.
"""
import csv
import datetime
import os
import random

DEFAULT_SEED = 412

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
REGIONS = {"Alpine": 1.0, "Coast": 0.8, "Lakes": 0.6}
CATEGORIES = {"Boots": (60, 220), "Clothing": (20, 120), "Packs": (40, 180), "Tents": (120, 480)}
COLUMNS = ["line_id", "order_date", "region", "category", "amount"]


def build(seed=DEFAULT_SEED):
    """Return {"sales": [row, ...]} with values as they appear in the CSV."""
    rng = random.Random(seed)
    rows = []
    day = datetime.date(2026, 1, 1)
    while day <= datetime.date(2026, 6, 30):
        season = 1 + 0.12 * (day.month - 1)
        for region, weight in REGIONS.items():
            for category, (low, high) in CATEGORIES.items():
                chance = 0.2 * weight * season * (1.4 if (region, category) == ("Coast", "Clothing") else 1)
                if rng.random() < chance:
                    rows.append({"order_date": day.isoformat(), "region": region, "category": category,
                                 "amount": "%.2f" % rng.uniform(low, high)})
        day += datetime.timedelta(days=1)
    for i, r in enumerate(rows):
        r["line_id"] = i + 1
    return {"sales": [{k: r[k] for k in COLUMNS} for r in rows]}


def main():
    os.makedirs(DATA, exist_ok=True)
    rows = build()["sales"]
    with open(os.path.join(DATA, "sales.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/sales.csv" % len(rows))


if __name__ == "__main__":
    main()
