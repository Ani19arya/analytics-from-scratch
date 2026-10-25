"""Build the synthetic sales table for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/sales.csv: one row per order, January 2025 to September 2026.
There are no rows in March 2025 (the shop was closed for a refit), which
is what makes "same period last year" tricky.
The data is synthetic and deterministic (fixed seed).
"""
import csv
import datetime
import os
import random

random.seed(402)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CATEGORIES = {"Beans": 18, "Equipment": 65, "Subscriptions": 30}
CHANNELS = ["Online", "Online", "Retail"]


def main():
    os.makedirs(DATA, exist_ok=True)
    rows = []
    day = datetime.date(2025, 1, 1)
    end = datetime.date(2026, 9, 30)
    while day <= end:
        if not (day.year == 2025 and day.month == 3):
            growth = 1.15 if day.year == 2026 else 1.0
            for _ in range(random.randint(1, 3)):
                category = random.choice(list(CATEGORIES))
                base = CATEGORIES[category] * growth
                amount = round(base * random.uniform(0.6, 1.8) * random.randint(1, 3), 2)
                rows.append({
                    "order_date": day.isoformat(),
                    "category": category,
                    "channel": random.choice(CHANNELS),
                    "amount": "%.2f" % amount,
                })
        day += datetime.timedelta(days=1)
    with open(os.path.join(DATA, "sales.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/sales.csv" % len(rows))


if __name__ == "__main__":
    main()
