"""Build the synthetic datasets for lesson 12.

Kestrel Home, a fictional online furniture shop.

data/orders.csv:   one row per first order from a new customer in October:
                   order_id and order_value in dollars. Most orders are small
                   items (lamps, chairs, rugs); about 1 in 7 is a sofa or a bed,
                   so the values have a long right tail. Two rows have a blank
                   order_value: the payment provider has not confirmed the amount.
data/sessions.csv: one row per website session in October: session_id,
                   user_id and revenue in dollars (0 when the session bought
                   nothing). Users come back many times, and some users are far
                   more likely to buy than others (and those also visit more),
                   so sessions from the same user are alike.

Run: python3 make_data.py          (writes both CSVs for the default seed)
Use: build(seed) returns {"orders": rows, "sessions": rows} without writing anything.
"""
import csv
import math
import os
import random

DEFAULT_SEED = 1212
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIELDS = {"orders": ["order_id", "order_value"], "sessions": ["session_id", "user_id", "revenue"]}
ORDERS = 160
PENDING = 2
USERS = 240


def build(seed=DEFAULT_SEED):
    """Return {"orders": rows, "sessions": rows}. The same seed always gives the same rows."""
    rng = random.Random(seed)
    orders = []
    for i in range(1, ORDERS + 1):
        if rng.random() < 0.15:
            value = rng.lognormvariate(math.log(1300), 0.3)
        else:
            value = rng.lognormvariate(math.log(150), 0.6)
        orders.append({"order_id": 70000 + i, "order_value": "%.2f" % value})
    for i in rng.sample(range(ORDERS), PENDING):
        orders[i]["order_value"] = ""

    visits = []
    for u in range(1, USERS + 1):
        buy_rate = rng.betavariate(0.4, 4)
        n_sessions = min(25, 1 + int(rng.expovariate(1 / (2.5 + 30 * buy_rate))))
        for _ in range(n_sessions):
            revenue = 0.0
            if rng.random() < buy_rate:
                revenue = rng.lognormvariate(math.log(220), 0.7)
            visits.append((3000 + u, revenue))
    rng.shuffle(visits)
    sessions = [{"session_id": 900000 + i, "user_id": user, "revenue": "%.2f" % rev}
                for i, (user, rev) in enumerate(visits, 1)]
    return {"orders": orders, "sessions": sessions}


def write_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_all(folder, tables):
    for name, rows in tables.items():
        write_csv(os.path.join(folder, name + ".csv"), rows, FIELDS[name])


def main():
    tables = build()
    write_all(DATA, tables)
    for name, rows in tables.items():
        print("wrote", len(rows), "rows to", os.path.join(DATA, name + ".csv"))


if __name__ == "__main__":
    main()
