"""Build data/orders.csv: three weeks of synthetic orders, Monday 5 to Sunday 25 October 2026.

Each order is paid or refunded. The refund chance is set higher in the last week,
but with this few orders the random draw can still go the other way: trust the
report, not the setting. Run: python3 make_data.py
"""
import csv
import os
import random
from datetime import date, timedelta

random.seed(504)

START = date(2026, 10, 5)
REFUND_PROB = [0.04, 0.04, 0.07]  # by week


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    rows, order_id = [], 5000
    for day in range(21):
        d = START + timedelta(days=day)
        for _ in range(random.randint(14, 30)):
            order_id += 1
            status = "refunded" if random.random() < REFUND_PROB[day // 7] else "paid"
            rows.append({"order_id": order_id, "order_date": d.isoformat(),
                         "customer_id": "C%03d" % random.randint(1, 300),
                         "amount": "%.2f" % random.uniform(20, 250), "status": status})
    with open(os.path.join(data, "orders.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["order_id", "order_date", "customer_id", "amount", "status"])
        w.writeheader()
        w.writerows(rows)
    print("wrote", len(rows), "orders")


if __name__ == "__main__":
    main()
