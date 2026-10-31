"""Build data/orders.csv: three weeks of synthetic orders, Monday 5 to Sunday 25 October 2026.

Each order is paid or refunded. The refund chance is set higher in the last week,
but with this few orders the random draw can still go the other way: trust the
report, not the setting.

    python3 make_data.py     # writes data/orders.csv for the default seed
    build(seed)              # returns {"orders": rows}, values as strings like the CSV
"""
import csv
import os
import random
from datetime import date, timedelta

DEFAULT_SEED = 504

START = date(2026, 10, 5)
REFUND_PROB = [0.04, 0.04, 0.07]  # by week
FIELDS = ["order_id", "order_date", "customer_id", "amount", "status"]


def build(seed=DEFAULT_SEED, days=21):
    rng = random.Random(seed)
    rows, order_id = [], 5000
    for day in range(days):
        d = START + timedelta(days=day)
        for _ in range(rng.randint(14, 30)):
            order_id += 1
            status = "refunded" if rng.random() < REFUND_PROB[min(day // 7, 2)] else "paid"
            rows.append({"order_id": str(order_id), "order_date": d.isoformat(),
                         "customer_id": "C%03d" % rng.randint(1, 300),
                         "amount": "%.2f" % rng.uniform(20, 250), "status": status})
    return {"orders": rows}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    rows = build()["orders"]
    with open(os.path.join(data, "orders.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print("wrote", len(rows), "orders")


if __name__ == "__main__":
    main()
