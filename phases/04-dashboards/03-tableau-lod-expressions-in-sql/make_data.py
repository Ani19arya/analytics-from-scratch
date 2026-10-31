"""Build the synthetic orders table for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/orders.csv: one row per order in 2025. Every customer belongs
to one region. A few customers place many orders, most place a few.
The data is synthetic and deterministic (fixed seed).

The test calls build(seed=...) with another seed to get a second,
different dataset in memory, so a query that hard-codes the answers fails.
"""
import csv
import datetime
import os
import random

DEFAULT_SEED = 403

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
REGIONS = ["Alpine", "Coast", "Lakes"]
COLUMNS = ["order_id", "customer_id", "region", "order_date", "amount"]


def build(seed=DEFAULT_SEED):
    """Return {"orders": [row, ...]} with values as they appear in the CSV."""
    rng = random.Random(seed)
    customers = []
    for n in range(1, 121):
        customers.append({
            "customer_id": "C%03d" % n,
            "region": rng.choice(REGIONS),
            "start": datetime.date(2025, 1, 1) + datetime.timedelta(days=rng.randint(0, 330)),
            "orders": rng.choice([1, 1, 2, 2, 3, 4, 6, 9]),
        })
    rows = []
    for c in customers:
        for _ in range(c["orders"]):
            day = c["start"] + datetime.timedelta(days=rng.randint(0, (datetime.date(2025, 12, 31) - c["start"]).days))
            rows.append({"customer_id": c["customer_id"], "region": c["region"],
                         "order_date": day.isoformat(), "amount": "%.2f" % rng.uniform(15, 260)})
        # Every customer's first order is on their start date.
        rows[-c["orders"]]["order_date"] = c["start"].isoformat()
    rows.sort(key=lambda r: (r["order_date"], r["customer_id"]))
    for i, r in enumerate(rows):
        r["order_id"] = "O%04d" % (i + 1)
    return {"orders": [{k: r[k] for k in COLUMNS} for r in rows]}


def main():
    os.makedirs(DATA, exist_ok=True)
    rows = build()["orders"]
    with open(os.path.join(DATA, "orders.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/orders.csv" % len(rows))


if __name__ == "__main__":
    main()
