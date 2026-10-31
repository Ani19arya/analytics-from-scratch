"""Build the synthetic Tiffinbell tables for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/customers.csv and data/orders.csv.
The data is synthetic and deterministic (fixed seed). Orders run from
3 August to 1 November 2026 (a Sunday), times to the second, amounts in
whole rupees.

The story built into the data: promo codes were typed by hand, so the same
festival code appears as FEST10, fest10 and Fest25. Orders come in on every
day of the week, including Sundays, so the day a week starts on matters.
Some customers ordered only once, so "days to the second order" is NULL for
them. A few customers placed two orders in the same second.

build(seed) returns the rows without writing anything. The test calls it with
a second seed to check your queries on data you have not seen.
"""
import csv
import datetime
import os
import random

SEED = 1414
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CITIES = [("Pune", 0.4), ("Mumbai", 0.3), ("Nashik", 0.15), ("Nagpur", 0.15)]
START = datetime.datetime(2026, 8, 3)
DAYS = 91  # 3 August to 1 November 2026
CODES = ["FEST10", "fest10", "Fest25", "FESTIVE", "WELCOME50", "welcome50", "BANKOFFER", "LOYALFEST"]


def pick_city(rng):
    x, acc = rng.random(), 0.0
    for name, share in CITIES:
        acc += share
        if x < acc:
            return name
    return CITIES[-1][0]


def build(seed=SEED):
    """Return {"customers": [...], "orders": [...]}."""
    rng = random.Random(seed)
    customers = []
    for i in range(1, 241):
        joined = START + datetime.timedelta(days=rng.randrange(DAYS - 10))
        customers.append({"customer_id": "C%04d" % i, "city": pick_city(rng),
                          "signed_up_on": joined.strftime("%Y-%m-%d")})
    orders = []
    n = 5001
    for c in customers:
        joined = datetime.datetime.strptime(c["signed_up_on"], "%Y-%m-%d")
        k = rng.choice([0, 1, 1, 1, 2, 3, 4, 5, 8, 12])
        for _ in range(k):
            day = joined + datetime.timedelta(days=rng.randrange((START + datetime.timedelta(days=DAYS) - joined).days))
            hour = rng.choice([8, 12, 13, 13, 19, 20, 20, 21, 22])
            t = day + datetime.timedelta(hours=hour, minutes=rng.randint(0, 59), seconds=rng.randint(0, 59))
            orders.append([t, c["customer_id"]])
        if k >= 2 and rng.random() < 0.08:  # a double tap: two orders in the same second
            orders.append([orders[-1][0], c["customer_id"]])
    orders.sort(key=lambda o: o[0])
    rows = []
    for t, cust in orders:
        promo = rng.choice(CODES) if rng.random() < 0.3 else ""
        rows.append({"order_id": n, "customer_id": cust, "ordered_at": t.strftime("%Y-%m-%d %H:%M:%S"),
                     "amount": rng.choice([60, 90, 140, 190, 220, 260]) * rng.choice([1, 1, 2, 2, 3]) + 30,
                     "status": "cancelled" if rng.random() < 0.08 else "completed",
                     "promo_code": promo})
        n += 1
    return {"customers": customers, "orders": rows}


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
