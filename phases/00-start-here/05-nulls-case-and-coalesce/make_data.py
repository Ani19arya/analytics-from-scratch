"""Build the synthetic orders table for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/orders.csv: Tiffinbell orders from 19 to 25 October 2026.
The data is synthetic and deterministic: the same seed always gives the same
rows. Tests call build(seed) for a second dataset.

Blank cells are on purpose:
- delivered_date is blank for cancelled and in_transit orders, and, because of a
  logging bug, for a few delivered orders too.
- amount is blank for a few orders whose payment record is missing.
- tip is recorded only for delivered orders, and only by the new app version.
  Blank means no tip was recorded. 0 means the customer chose not to tip.
"""
import csv
import datetime
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SEED = 8
CITIES = ["Mumbai", "Nagpur", "Nashik", "Pune"]
FIRST_DAY = datetime.date(2026, 10, 19)


def build(seed=DEFAULT_SEED):
    """Return {"orders": [rows]} where every value is text, exactly as in the CSV ("" for blank)."""
    rng = random.Random(seed)
    rows = []
    n = rng.randint(190, 230)
    for i in range(1, n + 1):
        day = FIRST_DAY + datetime.timedelta(days=rng.randint(0, 6))
        r = rng.random()
        status = "cancelled" if r < 0.07 else "in_transit" if r < 0.12 else "delivered"
        delivered = ""
        if status == "delivered" and rng.random() > 0.02:
            delivered = (day + datetime.timedelta(days=rng.choice([0, 0, 0, 1]))).isoformat()
        amount = "" if rng.random() < 0.025 else "%.2f" % rng.choice([rng.uniform(80, 300), rng.uniform(300, 800), rng.uniform(300, 800), rng.uniform(800, 2000)])
        old_app = rng.random() < 0.25
        tip = rng.choice(["0", "0", "0", "10", "20", "20", "30", "50"])
        if old_app or status != "delivered":
            tip = ""
        rows.append(
            {
                "order_id": str(90000 + i),
                "order_date": day.isoformat(),
                "city": rng.choice(CITIES),
                "status": status,
                "amount": amount,
                "delivered_date": delivered,
                "tip": tip,
            }
        )
    return {"orders": rows}


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
