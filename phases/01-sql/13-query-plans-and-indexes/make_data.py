"""Build the synthetic Tiffinbell tables for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/customers.csv and data/orders.csv.
The data is synthetic and deterministic (fixed seed). Orders run from
1 July to 31 October 2026, times to the second, amounts in whole rupees.

The committed files are a small sample (1,900 orders) of the kind of table
the dashboard reads. build(seed, n_orders) can make a bigger copy in memory,
so you can watch the cost of a query grow with the table. Most orders are
completed (about 93 percent), which matters for the index on status in
Common mistakes.

build(seed) returns the rows without writing anything. The test calls it with
a second seed to check your work on data you have not seen.
"""
import csv
import datetime
import os
import random

SEED = 1313
N_ORDERS = 1900
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CITIES = [("Pune", 0.4), ("Mumbai", 0.3), ("Nashik", 0.15), ("Nagpur", 0.15)]
START = datetime.datetime(2026, 7, 1)
DAYS = 123  # 1 July to 31 October 2026


def pick_city(rng):
    x, acc = rng.random(), 0.0
    for name, share in CITIES:
        acc += share
        if x < acc:
            return name
    return CITIES[-1][0]


def build(seed=SEED, n_orders=N_ORDERS):
    """Return {"customers": [...], "orders": [...]}, with n_orders orders."""
    rng = random.Random(seed)
    n_customers = max(50, n_orders // 6)
    customers = []
    for i in range(1, n_customers + 1):
        joined = START - datetime.timedelta(days=rng.randrange(200))
        customers.append({"customer_id": "T%05d" % i, "city": pick_city(rng),
                          "joined_on": joined.strftime("%Y-%m-%d")})
    stamps = []
    for _ in range(n_orders):
        day = START + datetime.timedelta(days=rng.randrange(DAYS))
        hour = rng.choice([8, 9, 12, 13, 13, 14, 19, 20, 20, 21, 22, 23])
        stamps.append(day + datetime.timedelta(hours=hour, minutes=rng.randint(0, 59), seconds=rng.randint(0, 59)))
    stamps.sort()
    orders = []
    for n, t in enumerate(stamps, 100001):
        # a few heavy customers order far more often than the rest
        if rng.random() < 0.2:
            cust = customers[rng.randrange(min(20, n_customers))]
        else:
            cust = rng.choice(customers)
        orders.append({"order_id": n, "customer_id": cust["customer_id"],
                       "ordered_at": t.strftime("%Y-%m-%d %H:%M:%S"),
                       "amount": rng.choice([60, 90, 140, 190, 220, 260]) * rng.choice([1, 1, 2, 2, 3]) + 30,
                       "status": "cancelled" if rng.random() < 0.07 else "completed"})
    return {"customers": customers, "orders": orders}


def write(name, rows):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/%s" % (len(rows), name))


def main():
    os.makedirs(DATA, exist_ok=True)
    tables = build()
    for name in ["customers", "orders"]:
        write(name + ".csv", tables[name])


if __name__ == "__main__":
    main()
