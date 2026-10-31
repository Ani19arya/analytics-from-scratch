"""Build the synthetic raw order feed for this lesson, as the nightly loader lands it.

Run from the lesson folder: python3 make_data.py
Writes data/raw_orders.csv. Everything is synthetic and deterministic (fixed
seed). Brightcart is a fictional online grocery; no row comes from a real system.

raw_orders.csv has one row per order PER VERSION, with the date it landed:
- load_date: the night the loader brought the row in. Only rows with
  load_date <= a run's date exist when that run happens.
- order_id, order_date, status, amount.
- Most orders land the same night. Some land 1 or 2 nights late (the
  payment system's export was slow).
- Some delivered orders are refunded later: a second row for the same order
  lands days after the first, with status "refunded". The latest load_date
  wins. One order never has two rows with the same load_date.

The extract covers 1 September to 31 October 2026 and stops at 31 October:
nothing that would land later is in it.

build(seed) returns the rows without writing anything. The test calls it with
a second seed: the volumes, the delays and the longest delay all change.
"""
import csv
import datetime
import os
import random

SEED = 803
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
START = datetime.date(2026, 9, 1)
END = datetime.date(2026, 10, 31)


def build(seed=SEED):
    """Return {"raw_orders": [...]}, rows as dicts of text, sorted by load_date then order_id."""
    rng = random.Random(seed)
    max_refund_delay = 9 if seed == SEED else rng.randint(5, 12)
    rows = []
    oid = 50001
    day = START
    while day <= END:
        for _ in range(rng.randint(12, 22)):
            status = "cancelled" if rng.random() < 0.08 else "delivered"
            amount = round(rng.lognormvariate(6.0, 0.5), 2)
            lag = rng.choices([0, 1, 2], weights=[80, 15, 5])[0]
            first = day + datetime.timedelta(days=lag)
            versions = [(first, status)]
            if status == "delivered" and rng.random() < 0.1:
                versions.append((first + datetime.timedelta(days=rng.randint(1, max_refund_delay)), "refunded"))
            for load, st in versions:
                if load <= END:
                    rows.append({"load_date": load.isoformat(), "order_id": oid, "order_date": day.isoformat(),
                                 "status": st, "amount": "%.2f" % amount})
            oid += 1
        day += datetime.timedelta(days=1)
    rows.sort(key=lambda r: (r["load_date"], r["order_id"]))
    return {"raw_orders": rows}


def main():
    os.makedirs(DATA, exist_ok=True)
    rows = build()["raw_orders"]
    with open(os.path.join(DATA, "raw_orders.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/raw_orders.csv" % len(rows))


if __name__ == "__main__":
    main()
