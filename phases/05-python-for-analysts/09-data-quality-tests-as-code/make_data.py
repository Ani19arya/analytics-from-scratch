"""Build two synthetic Kestrel Home files: two weeks of nightly order loads and the customer list.

Run from the lesson folder: python3 make_data.py
Writes:
  data/orders.csv      every row the nightly job loaded from 12 to 25 October 2026. load_date is
                       the night of the load; each load carries the previous day's orders.
  data/customers.csv   the customer list as of 11 October 2026
The data is synthetic and deterministic (fixed seed).

One load is broken on purpose. On that night the shop's export moved to a new version and the
job was retried, so the load:
- holds every row twice (the retry appended instead of replacing);
- has amounts in cents instead of dollars;
- has the status in capitals (PAID instead of paid) and an empty currency.
Normal nights are not perfect either: a few orders come from customers who signed up after the
customer list was taken, which is expected and only worth a warning.

The test calls build(seed=...) with another seed to get a second dataset in memory.
"""
import csv
import os
import random
from datetime import date, timedelta

DEFAULT_SEED = 509
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIRST_LOAD = date(2026, 10, 12)          # a Monday
LOADS = 14
STATUSES = ["paid"] * 17 + ["refunded"] * 2 + ["cancelled"]
ORDER_FIELDS = ["load_date", "order_id", "order_date", "customer_id", "status", "currency", "amount"]
CUSTOMER_FIELDS = ["customer_id", "signup_date"]


def build(seed=DEFAULT_SEED):
    """Return {"orders": rows, "customers": rows, "broken_load_date": "YYYY-MM-DD"}.
    Every cell is text, like csv.DictReader gives."""
    rng = random.Random(seed)
    n_customers = rng.randint(140, 170)
    customers = [{"customer_id": "C%04d" % (i + 1),
                  "signup_date": (date(2025, 1, 1) + timedelta(days=rng.randint(0, 640))).isoformat()}
                 for i in range(n_customers)]
    known = [c["customer_id"] for c in customers]
    new_id = n_customers

    loads = [FIRST_LOAD + timedelta(days=i) for i in range(LOADS)]
    # The broken night: a weekday in the second week, so a week of good loads comes before it.
    broken = rng.choice([d for d in loads[7:] if d.weekday() < 5])

    orders, order_no = [], 50001
    for load in loads:
        day = load - timedelta(days=1)
        weekend = day.weekday() >= 5
        batch = []
        for _ in range(rng.randint(54, 64) if weekend else rng.randint(44, 54)):
            if rng.random() < 0.025:
                new_id += 1
                customer = "C%04d" % new_id        # signed up after the list was taken
            else:
                customer = rng.choice(known)
            amount = round(rng.lognormvariate(5.3, 0.55), 2)
            amount = min(max(amount, 12.0), 1600.0)
            batch.append({"load_date": load.isoformat(), "order_id": "KO-%05d" % order_no,
                          "order_date": day.isoformat(), "customer_id": customer,
                          "status": rng.choice(STATUSES), "currency": "USD", "amount": "%.2f" % amount})
            order_no += 1
        if load == broken:
            for row in batch:
                row["amount"] = str(int(round(float(row["amount"]) * 100)))
                row["status"] = row["status"].upper()
                row["currency"] = ""
            batch = batch + [dict(r) for r in batch]
        orders.extend(batch)
    return {"orders": orders, "customers": customers, "broken_load_date": broken.isoformat()}


def main():
    os.makedirs(DATA, exist_ok=True)
    data = build()
    for name, fields in (("orders", ORDER_FIELDS), ("customers", CUSTOMER_FIELDS)):
        with open(os.path.join(DATA, name + ".csv"), "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(data[name])
        print("wrote %d rows to data/%s.csv" % (len(data[name]), name))


if __name__ == "__main__":
    main()
