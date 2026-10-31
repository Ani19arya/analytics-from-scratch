"""Build the synthetic orders table for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/orders.csv: Tiffinbell orders from Monday 12 October to Sunday
25 October 2026. The data is synthetic and deterministic: the same seed always
gives the same rows. Tests call build(seed) for a second dataset.

A few orders are bulk office lunches with large round amounts, so the biggest
orders include ties, and some big orders were cancelled.
"""
import csv
import datetime
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SEED = 36
CITIES = ["Mumbai", "Nagpur", "Nashik", "Pune"]
FIRST_DAY = datetime.date(2026, 10, 12)
DAYS = 14


def build(seed=DEFAULT_SEED):
    """Return {"orders": [rows]} where every value is text, exactly as in the CSV."""
    rng = random.Random(seed)
    rows = []
    for d in range(DAYS):
        day = FIRST_DAY + datetime.timedelta(days=d)
        for _ in range(rng.randint(16, 24)):
            if rng.random() < 0.06:
                amount = "%.2f" % rng.choice([1200, 1500, 1800, 2400, 3000, 3600])
            else:
                amount = "%.2f" % rng.uniform(90, 950)
            rows.append(
                {
                    "order_date": day.isoformat(),
                    "city": rng.choice(CITIES),
                    "status": "cancelled" if rng.random() < 0.08 else "delivered",
                    "amount": amount,
                }
            )
    out = []
    for i, r in enumerate(rows, 1):
        out.append({"order_id": str(80000 + i), "order_date": r["order_date"], "city": r["city"],
                    "status": r["status"], "amount": r["amount"]})
    return {"orders": out}


def main():
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    for name, rows in build().items():
        with open(os.path.join(HERE, "data", name + ".csv"), "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print("wrote %d rows to data/%s.csv" % (len(rows), name))


if __name__ == "__main__":
    main()
