"""Build the synthetic raw tables that this lesson's dbt-style project reads.

Run from the lesson folder: python3 make_data.py
Writes data/raw_orders.csv, data/raw_customers.csv and data/raw_payments.csv.
Everything is synthetic and deterministic (fixed seed). Brightcart is a
fictional online grocery.

The models in models/ are code and stay fixed. Only the data changes. Three
real-looking problems are planted, and the project's tests should catch them:
- a few customers appear twice in raw_customers (the CRM export repeated them),
- a few orders have status "Returned", a value the business has not defined,
- a few payments point at an order_id that is not in raw_orders (payments for
  orders placed in the test shop).

build(seed) returns the rows without writing anything. The test calls it with
a second seed: the counts of each problem change, and one of them is zero.
"""
import csv
import datetime
import os
import random

SEED = 802
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CITIES = ["Pune", "Mumbai", "Nagpur", "Nashik"]
STATUSES = ["delivered"] * 7 + ["cancelled", "refunded", "pending"]


def build(seed=SEED):
    """Return {"raw_orders": [...], "raw_customers": [...], "raw_payments": [...]}, rows as dicts."""
    rng = random.Random(seed)
    problems = {"dup_customers": 3, "returned": 4, "orphans": 3} if seed == SEED else {
        "dup_customers": rng.randint(1, 4), "returned": 0, "orphans": rng.randint(4, 7)}
    n_customers = rng.randint(110, 130)
    customers = []
    for cid in range(1, n_customers + 1):
        signup = datetime.date(2026, 5, 1) + datetime.timedelta(days=rng.randint(0, 150))
        customers.append({"customer_id": cid, "city": rng.choice(CITIES), "signup_date": signup.isoformat()})
    for cid in rng.sample(range(1, n_customers + 1), problems["dup_customers"]):
        twin = dict(customers[cid - 1])
        twin["city"] = " " + twin["city"] + " "  # same customer, exported twice
        customers.append(twin)
    customers.sort(key=lambda c: (c["customer_id"], c["city"]))
    orders, payments = [], []
    n_orders = rng.randint(380, 430)
    returned = set(rng.sample(range(n_orders), problems["returned"]))
    pid = 5001
    for k in range(n_orders):
        oid = 2001 + k
        day = datetime.date(2026, 9, 1) + datetime.timedelta(days=rng.randint(0, 60))
        status = "Returned" if k in returned else rng.choice(STATUSES)
        if status != "Returned" and rng.random() < 0.3:
            status = status.capitalize()
        amount = round(rng.lognormvariate(6.0, 0.5), 2)
        orders.append({"order_id": oid, "customer_id": rng.randint(1, n_customers), "order_date": day.isoformat(),
                       "status": status, "amount": "%.2f" % amount})
        if status.lower() != "pending":
            parts = [amount] if rng.random() < 0.85 else [round(amount * 0.6, 2), round(amount - round(amount * 0.6, 2), 2)]
            for part in parts:
                payments.append({"payment_id": pid, "order_id": oid, "method": rng.choice(["card", "upi", "cash"]),
                                 "amount": "%.2f" % part})
                pid += 1
    for _ in range(problems["orphans"]):
        payments.append({"payment_id": pid, "order_id": 9000 + rng.randint(0, 999), "method": "card",
                         "amount": "%.2f" % round(rng.uniform(100, 900), 2)})
        pid += 1
    return {"raw_orders": orders, "raw_customers": customers, "raw_payments": payments}


def write(name, rows):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/%s" % (len(rows), name))


def main():
    os.makedirs(DATA, exist_ok=True)
    tables = build()
    for name in ("raw_orders", "raw_customers", "raw_payments"):
        write(name + ".csv", tables[name])


if __name__ == "__main__":
    main()
