"""Build the synthetic orders and report period for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/orders.csv and data/report_period.csv.
The data is synthetic and deterministic (fixed seed). Amounts are whole
currency units, so totals are exact.

The story built into the data: Fernhill Supply ships wholesale orders from
three regions, North, South and West. The warehouse is shut on Sundays and
was shut on two other days (a power cut and a stock count), so those days
have no orders at all: no row, not a row with 0. A few orders have no region
yet, because the sales team had not assigned the account.

build(seed) returns the rows without writing anything. The test calls it with
a second seed to check your queries on data you have not seen.
"""
import csv
import datetime
import os
import random

SEED = 909
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIRST_DAY = datetime.date(2026, 9, 1)
LAST_DAY = datetime.date(2026, 10, 31)
REGIONS = [("North", 0.45, 900), ("South", 0.35, 700), ("West", 0.20, 1300)]  # name, share of orders, typical order


def pick_region(rng):
    if rng.random() < 0.015:
        return None, 800                     # account not assigned to a region yet
    x, acc = rng.random(), 0.0
    for name, share, typical in REGIONS:
        acc += share
        if x < acc:
            return name, typical
    return REGIONS[-1][0], REGIONS[-1][2]


def build(seed=SEED):
    """Return {"orders": [...], "report_period": [...]}, rows as dicts."""
    rng = random.Random(seed)
    days = [FIRST_DAY + datetime.timedelta(days=i) for i in range((LAST_DAY - FIRST_DAY).days + 1)]
    weekdays = [d for d in days if d.weekday() != 6]
    shut = set(rng.sample([d for d in weekdays if d > FIRST_DAY + datetime.timedelta(days=7)], 2))
    orders = []
    for d in days:
        if d.weekday() == 6 or d in shut:
            continue
        base = 9 if d.weekday() == 5 else 18   # Saturdays are half days
        trend = 1 + 0.004 * (d - FIRST_DAY).days
        for _ in range(max(1, int(rng.gauss(base * trend, 3)))):
            region, typical = pick_region(rng)
            orders.append({"order_date": d.isoformat(), "region": region,
                           "amount": int(typical * rng.uniform(0.5, 1.6))})
    orders = [dict(order_id=i, **o) for i, o in enumerate(orders, 1)]
    period = [{"start_date": FIRST_DAY.isoformat(), "end_date": LAST_DAY.isoformat()}]
    return {"orders": orders, "report_period": period}


def write(name, rows):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/%s" % (len(rows), name))


def main():
    os.makedirs(DATA, exist_ok=True)
    tables = build()
    write("orders.csv", tables["orders"])
    write("report_period.csv", tables["report_period"])


if __name__ == "__main__":
    main()
