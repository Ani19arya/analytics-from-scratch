"""Build the synthetic Larkspur Coffee wholesale files for this lesson.

Run from the lesson folder: python3 make_data.py
Writes:
  data/customers.csv   the customer master: one row per cafe account, with its region
  data/orders.csv      October 2026 wholesale orders, one row per order
The data is synthetic and deterministic (fixed seed).

In both files a quoted cell is text and an unquoted cell is a number, the way a
spreadsheet keeps the two apart. csv.QUOTE_NONNUMERIC writes and reads them that way.

The mess is added on purpose:
- orders typed in by the phone team carry the customer id as text ("1042"),
  and some of those also have a trailing space ("1042 ");
- two new accounts placed orders before anyone added them to the master;
- one account is in the master twice, with two different regions.

The test calls build(seed=...) with another seed to get a second dataset in memory.
"""
import csv
import os
import random
from datetime import date, timedelta

DEFAULT_SEED = 405
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
REGIONS = ["North", "South", "East", "West"]
FIRST = ["Alder", "Birch", "Cedar", "Dune", "Elm", "Fern", "Glen", "Heron", "Iris", "Juniper", "Kiln", "Linden"]
LAST = ["Cafe", "Bakery", "Deli", "Kitchen", "Roasters Bar"]
CUSTOMER_FIELDS = ["customer_id", "customer_name", "region"]
ORDER_FIELDS = ["order_id", "order_date", "channel", "customer_id", "amount"]


def build(seed=DEFAULT_SEED):
    """Return {"customers": rows, "orders": rows}. Numbers are floats and text is str,
    exactly what read_sheet gives back from the CSV files."""
    rng = random.Random(seed)
    n_customers = rng.randint(55, 65)
    ids = list(range(1001, 1001 + n_customers))
    customers = []
    for cid in ids:
        name = "%s %s" % (rng.choice(FIRST), rng.choice(LAST))
        customers.append({"customer_id": float(cid), "customer_name": name, "region": rng.choice(REGIONS)})

    # One account is in the master twice: it moved region and the old row was never deleted.
    dup_pos = rng.randrange(5, n_customers - 5)
    old = customers[dup_pos]
    moved = dict(old)
    moved["region"] = rng.choice([r for r in REGIONS if r != old["region"]])
    customers.insert(dup_pos + 1, moved)

    # Two new accounts order before they are added to the master.
    new_ids = [1001 + n_customers, 1002 + n_customers]

    orders = []
    n_orders = rng.randint(330, 380)
    for i in range(n_orders):
        cid = rng.choice(new_ids) if rng.random() < 0.025 else rng.choice(ids)
        channel = "phone" if rng.random() < 0.18 else "web"
        if channel == "phone":
            key = str(cid) + (" " if rng.random() < 0.4 else "")
        else:
            key = float(cid)
        day = date(2026, 10, 1) + timedelta(days=rng.randint(0, 30))
        amount = round(rng.uniform(40, 900), 2)
        orders.append({"order_id": float(70001 + i), "order_date": day.isoformat(), "channel": channel,
                       "customer_id": key, "amount": amount})
    # Make sure every kind of mess appears at least once, whatever the seed.
    orders[3]["channel"], orders[3]["customer_id"] = "phone", str(int(customers[0]["customer_id"])) + " "
    orders[5]["channel"], orders[5]["customer_id"] = "phone", str(int(customers[1]["customer_id"]))
    orders[8]["customer_id"] = float(new_ids[0])
    orders[13]["customer_id"] = old["customer_id"]
    return {"customers": customers, "orders": orders}


def write(path, rows, fields):
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_NONNUMERIC)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: (int(v) if isinstance(v, float) and k.endswith("_id") else v) for k, v in r.items()})


def main():
    os.makedirs(DATA, exist_ok=True)
    data = build()
    write(os.path.join(DATA, "customers.csv"), data["customers"], CUSTOMER_FIELDS)
    write(os.path.join(DATA, "orders.csv"), data["orders"], ORDER_FIELDS)
    print("wrote %d rows to data/customers.csv and %d rows to data/orders.csv"
          % (len(data["customers"]), len(data["orders"])))


if __name__ == "__main__":
    main()
