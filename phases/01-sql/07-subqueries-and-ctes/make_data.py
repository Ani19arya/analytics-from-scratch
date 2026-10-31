"""Build the synthetic customers and orders tables for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/customers.csv and data/orders.csv.
The data is synthetic and deterministic (fixed seed). Orders are from
October 2026 and amounts are whole rupees.

The story built into the data: Tiffinbell delivers in four cities, prices
differ by city, and spending is uneven. Most customers order a few small
lunches, a few order often or order big office lunches, and some customers
did not order at all in October.

build(seed) returns the rows without writing anything. The test calls it with
a second seed to check your queries on data you have not seen.
"""
import csv
import datetime
import os
import random

SEED = 707
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CITIES = [("Pune", 0.4, 260), ("Mumbai", 0.3, 320), ("Nashik", 0.15, 210), ("Nagpur", 0.15, 230)]  # name, share, typical order
FIRST = ["Aditi", "Bhavin", "Chitra", "Dev", "Esha", "Farhan", "Gauri", "Harsh", "Ira", "Jay", "Kiran", "Lata",
         "Manav", "Nisha", "Om", "Pooja", "Rohan", "Sana", "Tanvi", "Uday", "Vani", "Yash", "Zoya"]


def pick_city(rng):
    x, acc = rng.random(), 0.0
    for name, share, typical in CITIES:
        acc += share
        if x < acc:
            return name, typical
    return CITIES[-1][0], CITIES[-1][2]


def build(seed=SEED):
    """Return {"customers": [...], "orders": [...]}, rows as dicts."""
    rng = random.Random(seed)
    customers, orders = [], []
    for i in range(1, 181):
        cid = "T%03d" % i
        city, typical = pick_city(rng)
        name = "%s %s." % (rng.choice(FIRST), chr(ord("A") + rng.randint(0, 25)))
        customers.append({"customer_id": cid, "name": name, "city": city})
        kind = rng.random()
        if kind < 0.12:
            n = 0                      # no order in October
        elif kind < 0.85:
            n = rng.randint(1, 4)      # a few lunches
        else:
            n = rng.randint(6, 14)     # a regular
        for _ in range(n):
            amount = int(typical * rng.uniform(0.6, 1.5))
            if rng.random() < 0.06:
                amount *= rng.randint(4, 8)  # an office lunch for the team
            orders.append({"customer_id": cid,
                           "order_date": datetime.date(2026, 10, rng.randint(1, 31)).isoformat(),
                           "amount": amount})
    orders.sort(key=lambda r: (r["order_date"], r["customer_id"], r["amount"]))
    orders = [{"order_id": n, "customer_id": r["customer_id"], "order_date": r["order_date"], "amount": r["amount"]}
              for n, r in enumerate(orders, 1)]
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
    write("customers.csv", tables["customers"])
    write("orders.csv", tables["orders"])


if __name__ == "__main__":
    main()
