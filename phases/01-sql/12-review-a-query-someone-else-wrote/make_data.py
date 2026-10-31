"""Build the synthetic Tiffinbell tables for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/customers.csv, data/orders.csv, data/order_items.csv and
data/promo_redemptions.csv.
The data is synthetic and deterministic (fixed seed). Orders run from
25 September to 4 November 2026, times to the second, amounts in whole rupees.

The story built into the data: most orders have two or more item lines, so a
join to order_items repeats each order. About a third of orders used a promo
code, and a few of those were staff codes. Orders come in all day, including
late on 31 October (a Saturday night). Some orders were cancelled.

build(seed) returns the rows without writing anything. The test calls it with
a second seed to check your queries on data you have not seen.
"""
import csv
import datetime
import os
import random

SEED = 1212
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CITIES = [("Pune", 0.4, 260), ("Mumbai", 0.3, 320), ("Nashik", 0.15, 210), ("Nagpur", 0.15, 230)]
START = datetime.datetime(2026, 9, 25)
DAYS = 41
ITEMS = [("Dal tadka", 140), ("Paneer thali", 220), ("Veg biryani", 190), ("Chicken biryani", 260),
         ("Poha", 60), ("Misal pav", 90), ("Gulab jamun", 70), ("Lassi", 80), ("Roti (4)", 50)]


def pick_city(rng):
    x, acc = rng.random(), 0.0
    for name, share, typical in CITIES:
        acc += share
        if x < acc:
            return name
    return CITIES[-1][0]


def build(seed=SEED):
    """Return {"customers": [...], "orders": [...], "order_items": [...], "promo_redemptions": [...]}."""
    rng = random.Random(seed)
    customers = [{"customer_id": "T%03d" % i, "city": pick_city(rng)} for i in range(1, 161)]
    stamps = []
    for _ in range(620):
        day = START + datetime.timedelta(days=rng.randrange(DAYS))
        hour = rng.choice([8, 9, 12, 13, 13, 14, 19, 20, 20, 21, 22, 23])
        stamps.append(day + datetime.timedelta(hours=hour, minutes=rng.randint(0, 59), seconds=rng.randint(0, 59)))
    for _ in range(14):  # Saturday night, 31 October: a late rush
        stamps.append(datetime.datetime(2026, 10, 31, rng.randint(18, 23), rng.randint(0, 59), rng.randint(0, 59)))
    stamps.sort()
    orders, items, promos = [], [], []
    for n, t in enumerate(stamps, 1001):
        lines = rng.choice([1, 1, 2, 2, 2, 3, 3, 4])
        amount = 0
        for line in range(1, lines + 1):
            name, price = rng.choice(ITEMS)
            qty = rng.choice([1, 1, 1, 2, 2, 3])
            amount += qty * price
            items.append({"order_id": n, "line_no": line, "item": name, "qty": qty})
        status = "cancelled" if rng.random() < 0.07 else "completed"
        if rng.random() < 0.35:
            channel = rng.choice(["app", "app", "app", "partner", "staff"])
            code = {"app": "TIFFIN50", "partner": "BANKOFFER", "staff": "STAFF30"}[channel]
            amount = int(amount * (0.7 if channel == "staff" else 0.85))
            promos.append({"order_id": n, "promo_code": code, "channel": channel})
        amount += 30  # delivery fee
        orders.append({"order_id": n, "customer_id": rng.choice(customers)["customer_id"],
                       "ordered_at": t.strftime("%Y-%m-%d %H:%M:%S"), "amount": amount, "status": status})
    return {"customers": customers, "orders": orders, "order_items": items, "promo_redemptions": promos}


def write(name, rows):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/%s" % (len(rows), name))


def main():
    os.makedirs(DATA, exist_ok=True)
    tables = build()
    for name in ["customers", "orders", "order_items", "promo_redemptions"]:
        write(name + ".csv", tables[name])


if __name__ == "__main__":
    main()
