"""Build the synthetic sales table for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/sales.csv: one row per order, January 2025 to September 2026.
There are no rows at all in March 2025: the roastery closed for a refit, so
nothing shipped, online or from the shop. That gap is what makes "same
period last year" tricky.
The data is synthetic and deterministic (fixed seed).

The test calls build(seed=...) with another seed to get a second,
different dataset in memory, so a query that hard-codes the answers fails.
"""
import csv
import datetime
import os
import random

DEFAULT_SEED = 402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CATEGORIES = {"Beans": 18, "Equipment": 65, "Subscriptions": 30}
CHANNELS = ["Online", "Online", "Retail"]


def build(seed=DEFAULT_SEED):
    """Return {"sales": [row, ...]} with values as they appear in the CSV."""
    rng = random.Random(seed)
    rows = []
    day = datetime.date(2025, 1, 1)
    end = datetime.date(2026, 9, 30)
    while day <= end:
        if not (day.year == 2025 and day.month == 3):
            growth = 1.15 if day.year == 2026 else 1.0
            for _ in range(rng.randint(1, 3)):
                category = rng.choice(list(CATEGORIES))
                base = CATEGORIES[category] * growth
                amount = round(base * rng.uniform(0.6, 1.8) * rng.randint(1, 3), 2)
                rows.append({
                    "order_date": day.isoformat(),
                    "category": category,
                    "channel": rng.choice(CHANNELS),
                    "amount": "%.2f" % amount,
                })
        day += datetime.timedelta(days=1)
    return {"sales": rows}


def main():
    os.makedirs(DATA, exist_ok=True)
    rows = build()["sales"]
    with open(os.path.join(DATA, "sales.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/sales.csv" % len(rows))


if __name__ == "__main__":
    main()
