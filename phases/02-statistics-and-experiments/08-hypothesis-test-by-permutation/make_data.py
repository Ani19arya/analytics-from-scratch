"""Build the synthetic datasets for lesson 08.

data/orders.csv: Harbor Mealkits' side dish test (synthetic). One row per
                 customer: customer_id, group ("control" saw the usual recipe
                 page, "side_dish" saw a suggested side dish) and order_value,
                 the value of that customer's next order in dollars. Two rows
                 have a blank order_value: the order was placed but its value
                 failed to log.
data/pilot.csv:  the 10-customer pilot run the week before (synthetic), 5 per
                 group, small enough to check every possible split by hand.

Order values: most are a regular box for two, about 12% are a big family box,
so the values have a long right tail. In the side_dish group about 30% of
customers add a side for 6 to 14 dollars. Customers are split 50/50.

Run: python3 make_data.py          (writes both CSVs for the default seed)
Use: build(seed) returns {"orders": rows, "pilot": rows} without writing anything.
"""
import csv
import math
import os
import random

DEFAULT_SEED = 924
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIELDS = ["customer_id", "group", "order_value"]
CUSTOMERS = 72
PILOT_PER_GROUP = 5
BLANKS = 2


def order_value(rng, group):
    if rng.random() < 0.12:
        value = rng.lognormvariate(math.log(105), 0.25)
    else:
        value = rng.lognormvariate(math.log(47), 0.25)
    if group == "side_dish" and rng.random() < 0.30:
        value += rng.uniform(6, 14)
    return round(value, 2)


def build(seed=DEFAULT_SEED):
    """Return {"orders": rows, "pilot": rows}. The same seed always gives the same rows."""
    rng = random.Random(seed)
    groups = ["control"] * (CUSTOMERS // 2) + ["side_dish"] * (CUSTOMERS // 2)
    rng.shuffle(groups)
    orders = []
    for i, group in enumerate(groups, 1):
        orders.append({"customer_id": 1000 + i, "group": group, "order_value": order_value(rng, group)})
    for i in sorted(rng.sample(range(len(orders)), BLANKS)):
        orders[i]["order_value"] = ""
    pilot_groups = ["control"] * PILOT_PER_GROUP + ["side_dish"] * PILOT_PER_GROUP
    rng.shuffle(pilot_groups)
    pilot = [{"customer_id": 900 + i, "group": g, "order_value": order_value(rng, g)}
             for i, g in enumerate(pilot_groups, 1)]
    return {"orders": orders, "pilot": pilot}


def write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def write_all(folder, tables):
    for name, rows in tables.items():
        write_csv(os.path.join(folder, name + ".csv"), rows)


def main():
    tables = build()
    write_all(DATA, tables)
    for name, rows in tables.items():
        print("wrote", len(rows), "rows to", os.path.join(DATA, name + ".csv"))


if __name__ == "__main__":
    main()
