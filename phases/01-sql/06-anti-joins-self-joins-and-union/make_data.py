"""Build the synthetic customers, web_orders and app_orders tables for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/customers.csv, data/web_orders.csv and data/app_orders.csv.
The data is synthetic and deterministic (fixed seed). Orders run from
1 February to 30 April 2026.

The story built into the data:
- Brightcart sells fixed-price grocery boxes (24, 36, 48 or 60), so many
  orders share the same date and amount.
- Orders come from two systems that number their orders separately, both
  starting at 1. The website allows guest checkout, so a web order can have
  no customer_id. The app always has one.
- referred_by is the customer_id of the customer who referred this one, or
  empty. A customer can only be referred by someone who joined earlier.

build(seed) returns the rows without writing anything. The test calls it with
a second seed to check your queries on data you have not seen.
"""
import csv
import datetime
import os
import random

SEED = 606
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CITIES = ["Austin", "Denver", "Pune", "Leeds", "Perth"]
FIRST = ["Aarav", "Bea", "Chen", "Dara", "Eli", "Farah", "Gus", "Hana", "Ivo", "Jaya", "Kofi", "Lena",
         "Mo", "Nia", "Omar", "Pia", "Quinn", "Ravi", "Sol", "Tara", "Uma", "Vik", "Wren", "Yara", "Zed"]
PRICES = [24.0, 36.0, 48.0, 60.0]
MONTHS = [(2, 28), (3, 31), (4, 30)]  # (month, days) in 2026


def build(seed=SEED):
    """Return {"customers": [...], "web_orders": [...], "app_orders": [...]}, rows as dicts."""
    rng = random.Random(seed)
    customers = []
    for i in range(1, 141):
        cid = "C%03d" % i
        referred_by = ""
        if i > 5 and rng.random() < 0.35:
            referred_by = "C%03d" % rng.randint(1, i - 1)
        name = "%s %s." % (rng.choice(FIRST), chr(ord("A") + rng.randint(0, 25)))
        customers.append({"customer_id": cid, "name": name, "city": rng.choice(CITIES), "referred_by": referred_by})

    web, app = [], []
    for c in customers:
        # Each customer has a chance of ordering in each month; some drift away in April.
        keen = rng.uniform(0.3, 0.9)
        drop = rng.random() < 0.3
        for month, days in MONTHS:
            p = keen * (0.35 if (drop and month == 4) else 1.0)
            if rng.random() > p:
                continue
            for _ in range(rng.randint(1, 3)):
                row = {"customer_id": c["customer_id"],
                       "order_date": datetime.date(2026, month, rng.randint(1, days)).isoformat(),
                       "amount": rng.choice(PRICES)}
                (app if rng.random() < 0.45 else web).append(row)
    # Guest checkouts on the website: no customer_id, but real revenue.
    for month, days in MONTHS:
        for _ in range(rng.randint(5, 9)):
            web.append({"customer_id": "", "order_date": datetime.date(2026, month, rng.randint(1, days)).isoformat(),
                        "amount": rng.choice(PRICES)})

    def number(rows):
        rows.sort(key=lambda r: (r["order_date"], r["customer_id"], r["amount"]))
        return [{"order_id": n, "customer_id": r["customer_id"], "order_date": r["order_date"], "amount": r["amount"]}
                for n, r in enumerate(rows, 1)]

    return {"customers": customers, "web_orders": number(web), "app_orders": number(app)}


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
    write("web_orders.csv", tables["web_orders"])
    write("app_orders.csv", tables["app_orders"])


if __name__ == "__main__":
    main()
