"""Build the synthetic Tiffinbell order file and monthly targets for this lesson.

Run from the lesson folder: python3 make_data.py
Writes:
  data/orders.csv    one row per order, 1 September to 20 October 2026, four cities
  data/targets.csv   the monthly targets the CEO's dashboard compares against
The data is synthetic and deterministic (fixed seed). Nashik is the newest kitchen and
takes only a handful of orders a day, so its rates rest on small numbers.

The test calls build(seed=..., end=...) to get a second dataset in memory, ending on
another day, so code that hard-codes 20 October or the committed totals fails.
"""
import csv
import os
import random
from datetime import date, timedelta

DEFAULT_SEED = 407
DEFAULT_END = date(2026, 10, 20)
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CITIES = {"Pune": 11.0, "Mumbai": 9.0, "Nagpur": 6.0, "Nashik": 1.0}   # average orders a day in September
FIELDS = ["order_id", "order_date", "city", "amount", "refunded"]


def poisson(rng, mean):
    """Number of orders in a day, drawn the slow simple way (Knuth's method)."""
    limit, k, p = pow(2.718281828459045, -mean), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def build(seed=DEFAULT_SEED, end=DEFAULT_END):
    """Return {"orders": rows, "targets": rows}. Orders run from 1 September 2026 to `end`."""
    rng = random.Random(seed)
    growth = rng.uniform(1.02, 1.12)          # October orders a day relative to September
    refund_base = rng.uniform(0.025, 0.045)
    orders, oid, d = [], 500001, date(2026, 9, 1)
    while d <= end:
        weekend = 1.25 if d.weekday() >= 5 else 1.0
        month_factor = growth if d.month == 10 else 1.0
        for city in sorted(CITIES):
            for _ in range(poisson(rng, CITIES[city] * weekend * month_factor)):
                amount = round(rng.uniform(150, 650), 2)
                refund_p = refund_base * (2.0 if city == "Nashik" else 1.0)
                orders.append({"order_id": oid, "order_date": d.isoformat(), "city": city,
                               "amount": amount, "refunded": 1 if rng.random() < refund_p else 0})
                oid += 1
        d += timedelta(days=1)
    targets = []
    for month, revenue, n_orders in (("2026-09", 320000, 860), ("2026-10", 360000, 960)):
        targets.append({"month": month, "kpi": "revenue", "target": revenue})
        targets.append({"month": month, "kpi": "orders", "target": n_orders})
        targets.append({"month": month, "kpi": "refund_rate", "target": 4.0})
    return {"orders": orders, "targets": targets}


def main():
    os.makedirs(DATA, exist_ok=True)
    data = build()
    for name, fields in (("orders", FIELDS), ("targets", ["month", "kpi", "target"])):
        with open(os.path.join(DATA, name + ".csv"), "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(data[name])
        print("wrote %d rows to data/%s.csv" % (len(data[name]), name))


if __name__ == "__main__":
    main()
