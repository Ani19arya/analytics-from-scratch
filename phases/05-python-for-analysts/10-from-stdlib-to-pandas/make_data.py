"""Build data/orders.csv: one month of synthetic Juniper Bikes online orders.

Run from the lesson folder: python3 make_data.py
The data is synthetic and deterministic (fixed seed).

Things a reader must handle, on purpose:
- region "NA" means North America, a real value that pandas reads as missing by default;
- a few orders have a blank region (the address could not be matched);
- a few orders have a blank amount (not invoiced yet);
- a handful of rows appear twice, word for word (two exports overlapped).

The test calls build(seed=...) with another seed to get a second dataset in memory.
"""
import csv
import os
import random
from datetime import date, timedelta

DEFAULT_SEED = 510
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
REGIONS = ["EU"] * 4 + ["UK"] * 3 + ["NA"] * 4 + ["APAC"] * 2
CHANNELS = ["web", "web", "web", "store"]
FIELDS = ["order_id", "order_date", "region", "channel", "qty", "amount"]


def build(seed=DEFAULT_SEED):
    """Return {"orders": rows}, every cell as text, like csv.DictReader gives."""
    rng = random.Random(seed)
    rows = []
    for i in range(rng.randint(520, 600)):
        qty = rng.choice([1, 1, 1, 1, 2, 2, 3])
        price = rng.choice([19.0, 45.0, 89.0, 240.0, 610.0, 1150.0, 2300.0])
        amount = "" if rng.random() < 0.02 else "%.2f" % (qty * price)
        region = "" if rng.random() < 0.03 else rng.choice(REGIONS)
        rows.append({"order_id": "J-%05d" % (30001 + i),
                     "order_date": (date(2026, 10, 1) + timedelta(days=rng.randint(0, 30))).isoformat(),
                     "region": region, "channel": rng.choice(CHANNELS), "qty": str(qty), "amount": amount})
    for _ in range(rng.randint(4, 7)):                 # two exports overlapped
        r = rng.choice(rows)
        rows.insert(rows.index(r) + 1, dict(r))
    return {"orders": rows}


def main():
    os.makedirs(DATA, exist_ok=True)
    rows = build()["orders"]
    with open(os.path.join(DATA, "orders.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/orders.csv" % len(rows))


if __name__ == "__main__":
    main()
