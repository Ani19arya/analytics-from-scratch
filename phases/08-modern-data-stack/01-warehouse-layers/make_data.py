"""Build the synthetic raw tables for this lesson, exactly as a loader lands them.

Run from the lesson folder: python3 make_data.py
Writes data/raw_orders.csv and data/raw_customers.csv.
Everything is synthetic and deterministic (fixed seed). Brightcart is a
fictional online grocery; no row comes from a real system.

The raw layer is what the source systems sent, untouched, so it is messy on purpose:
- raw_orders.csv: one row per order PER LOAD. The loader runs every night and
  re-sends orders that changed, so an order can appear more than once; the row
  with the highest load_id is the latest version. ordered_at comes in two
  formats (the old app wrote DD/MM/YYYY HH:MM, the new one YYYY-MM-DD HH:MM:SS).
  status is in mixed case. amount is text, sometimes with a thousands comma,
  and empty when the payment system had not answered yet. discount is a number.
- raw_customers.csv: one row per customer per load, latest load wins. city has
  stray spaces and mixed case, or is empty. Some orders belong to customers
  whose row has not arrived yet (the customer load runs after the order load).

build(seed) returns the rows without writing anything. The test calls it with a
second seed: the cities, counts, duplicates and messy values all change.
"""
import csv
import datetime
import os
import random

SEED = 801
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CITY_SETS = {
    801: ["Pune", "Mumbai", "Nagpur", "Nashik", "Thane"],
}
OTHER_CITIES = ["Indore", "Bhopal", "Surat", "Pune", "Jaipur"]
STATUSES = ["delivered"] * 7 + ["cancelled", "refunded", "pending"]


def messy_city(rng, city):
    style = rng.random()
    if style < 0.15:
        return " " + city.lower()
    if style < 0.3:
        return city.upper() + " "
    return city


def messy_status(rng, status):
    style = rng.random()
    if style < 0.2:
        return status.upper()
    if style < 0.4:
        return status.capitalize()
    return status


def money_text(rng, value):
    text = "%.2f" % value
    if value >= 1000 and rng.random() < 0.7:
        whole, cents = text.split(".")
        text = "{:,}".format(int(whole)) + "." + cents
    elif rng.random() < 0.2:
        text = text.rstrip("0").rstrip(".")  # 45.50 written as 45.5
    return text


def build(seed=SEED):
    """Return {"raw_orders": [...], "raw_customers": [...]}, rows as dicts of text, like the CSV files."""
    rng = random.Random(seed)
    cities = CITY_SETS.get(seed, OTHER_CITIES)
    n_customers = rng.randint(130, 160)
    customers = []
    for cid in range(1, n_customers + 1):
        city = rng.choice(cities)
        signup = datetime.date(2026, 6, 1) + datetime.timedelta(days=rng.randint(0, 120))
        customers.append({"customer_id": cid, "city": city, "signup_date": signup.isoformat()})
    raw_customers = []
    late = set(rng.sample(range(1, n_customers + 1), 4))  # their rows have not landed yet
    for c in customers:
        if c["customer_id"] in late:
            continue
        load = rng.randint(1, 20)
        city = "" if rng.random() < 0.04 else messy_city(rng, c["city"])
        raw_customers.append({"load_id": load, "customer_id": c["customer_id"], "city": city,
                              "signup_date": c["signup_date"]})
        if rng.random() < 0.12:  # the customer moved: a later load sends the new city
            moved = rng.choice([x for x in cities if x != c["city"]])
            raw_customers.append({"load_id": load + rng.randint(1, 30), "customer_id": c["customer_id"],
                                  "city": messy_city(rng, moved), "signup_date": c["signup_date"]})
    raw_orders = []
    n_orders = rng.randint(560, 640)
    for oid in range(1001, 1001 + n_orders):
        cust = rng.randint(1, n_customers)
        ts = datetime.datetime(2026, 8, 1) + datetime.timedelta(minutes=rng.randint(0, 91 * 24 * 60 - 1))
        status = rng.choice(STATUSES)
        amount = round(rng.lognormvariate(6.2, 0.6), 2)
        discount = round(amount * rng.choice([0, 0, 0, 0.05, 0.1]), 2)
        load = (ts.date() - datetime.date(2026, 8, 1)).days + 1
        old_app = rng.random() < 0.3
        when = ts.strftime("%d/%m/%Y %H:%M") if old_app else ts.strftime("%Y-%m-%d %H:%M:%S")
        versions = []
        if status in ("cancelled", "refunded") and rng.random() < 0.6:
            versions.append("pending")  # first landed as pending, changed later
        versions.append(status)
        if rng.random() < 0.05:
            versions.append(status)  # the loader re-sent an unchanged row
        for k, st in enumerate(versions):
            missing = k == 0 and len(versions) > 1 and rng.random() < 0.3
            raw_orders.append({"load_id": load + k * rng.randint(1, 5), "order_id": oid, "customer_id": cust,
                               "ordered_at": when, "status": messy_status(rng, st),
                               "amount": "" if missing else money_text(rng, amount), "discount": "%.2f" % discount})
        if rng.random() < 0.02 and len(versions) == 1:  # payment never answered: amount still empty
            raw_orders[-1]["amount"] = ""
    raw_orders.sort(key=lambda r: (r["load_id"], r["order_id"]))
    raw_customers.sort(key=lambda r: (r["load_id"], r["customer_id"]))
    return {"raw_orders": raw_orders, "raw_customers": raw_customers}


def write(name, rows):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/%s" % (len(rows), name))


def main():
    os.makedirs(DATA, exist_ok=True)
    tables = build()
    write("raw_orders.csv", tables["raw_orders"])
    write("raw_customers.csv", tables["raw_customers"])


if __name__ == "__main__":
    main()
