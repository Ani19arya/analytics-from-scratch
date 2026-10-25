"""Build the synthetic orders table for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/orders.csv: one row per order in 2025. Every customer belongs
to one region. A few customers place many orders, most place a few.
The data is synthetic and deterministic (fixed seed).
"""
import csv
import datetime
import os
import random

random.seed(403)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
REGIONS = ["Alpine", "Coast", "Lakes"]


def main():
    os.makedirs(DATA, exist_ok=True)
    customers = []
    for n in range(1, 121):
        customers.append({
            "customer_id": "C%03d" % n,
            "region": random.choice(REGIONS),
            "start": datetime.date(2025, 1, 1) + datetime.timedelta(days=random.randint(0, 330)),
            "orders": random.choice([1, 1, 2, 2, 3, 4, 6, 9]),
        })
    rows = []
    for c in customers:
        for _ in range(c["orders"]):
            day = c["start"] + datetime.timedelta(days=random.randint(0, (datetime.date(2025, 12, 31) - c["start"]).days))
            rows.append({"customer_id": c["customer_id"], "region": c["region"],
                         "order_date": day.isoformat(), "amount": "%.2f" % random.uniform(15, 260)})
        # Every customer's first order is on their start date.
        rows[-c["orders"]]["order_date"] = c["start"].isoformat()
    rows.sort(key=lambda r: (r["order_date"], r["customer_id"]))
    for i, r in enumerate(rows):
        r["order_id"] = "O%04d" % (i + 1)
    cols = ["order_id", "customer_id", "region", "order_date", "amount"]
    with open(os.path.join(DATA, "orders.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows([{k: r[k] for k in cols} for r in rows])
    print("wrote %d rows to data/orders.csv" % len(rows))


if __name__ == "__main__":
    main()
