"""Build the synthetic customer change log and orders for this lesson.

Run from the lesson folder: python3 make_data.py
Writes two files to data/:
  customer_changes.csv  the CRM's change log: one row each time a customer's
                        record was saved, with the region on that record and the
                        date the change took effect. change_id is the load order.
                        The log is messy on purpose:
                        - most saves change the street, not the region, so the
                          region repeats from one row to the next;
                        - a few regions were typed wrong and corrected the same
                          day (the later change_id is the right one);
                        - a few moves were entered late, so a later change_id can
                          have an earlier changed_on.
  orders.csv            one row per order, January 2025 to September 2026. The
                        change log only starts on 1 March 2025, so a few early
                        orders come before the customer's first record.
The data is synthetic and deterministic (fixed seed).

The test calls build(seed=...) with another seed to get a second,
different dataset in memory, so a query that hard-codes the answers fails.
"""
import csv
import datetime
import os
import random

DEFAULT_SEED = 410

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
REGIONS = ["Alpine", "Coast", "Lakes"]
LOG_START = datetime.date(2025, 3, 1)
FIRST_ORDER, LAST_ORDER = datetime.date(2025, 1, 1), datetime.date(2026, 9, 30)


def day_after(start, max_days, rng):
    return start + datetime.timedelta(days=rng.randint(1, max_days))


def build(seed=DEFAULT_SEED):
    """Return {"customer_changes": [...], "orders": [...]} with values as they appear in the CSV files."""
    rng = random.Random(seed)
    changes, orders = [], []
    for n in range(1, 91):
        cid = "C%03d" % n
        legacy = n % 9 == 0                      # bought before the change log existed
        start = LOG_START if legacy else LOG_START + datetime.timedelta(days=rng.randint(0, 300))
        region = rng.choice(REGIONS)
        saves = [(start, region)]
        day = start
        for _ in range(rng.choice([0, 0, 1, 1, 2, 3])):
            day = day_after(day, 150, rng)
            if day >= LAST_ORDER:
                break
            if rng.random() < 0.45:              # a real move
                region = rng.choice([r for r in REGIONS if r != region])
            saves.append((day, region))          # otherwise a new street, same region
        late = [rng.random() < 0.15 and day > start for day, _ in saves]
        if rng.random() < 0.12:                  # typed wrong, fixed the same day
            day, right = saves[-1]
            wrong = rng.choice([r for r in REGIONS if r != right])
            saves = saves[:-1] + [(day, wrong), (day, right)]
            late = late[:-1] + [late[-1], late[-1]]
        for (day, reg), is_late in zip(saves, late):
            changes.append({"customer_id": cid, "region": reg, "changed_on": day.isoformat(), "late": is_late})
        first_buy = FIRST_ORDER + datetime.timedelta(days=rng.randint(0, 50)) if legacy else start
        for _ in range(rng.choice([1, 2, 3, 4, 5, 6, 8, 10])):
            span = (LAST_ORDER - first_buy).days
            orders.append({"customer_id": cid, "order_date": (first_buy + datetime.timedelta(
                days=rng.randint(0, span))).isoformat(), "amount": "%.2f" % rng.uniform(20, 240)})
    # change_id is load order: by date, except late entries, which load at the end.
    changes.sort(key=lambda c: (c["late"], c["changed_on"] if not c["late"] else "", c["customer_id"]))
    out_changes = [{"change_id": i + 1, "customer_id": c["customer_id"], "region": c["region"],
                    "changed_on": c["changed_on"]} for i, c in enumerate(changes)]
    orders.sort(key=lambda o: (o["order_date"], o["customer_id"], o["amount"]))
    out_orders = [{"order_id": "O%04d" % (i + 1), "customer_id": o["customer_id"], "order_date": o["order_date"],
                   "amount": o["amount"]} for i, o in enumerate(orders)]
    return {"customer_changes": out_changes, "orders": out_orders}


def main():
    os.makedirs(DATA, exist_ok=True)
    for name, rows in build().items():
        with open(os.path.join(DATA, name + ".csv"), "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print("wrote %d rows to data/%s.csv" % (len(rows), name))


if __name__ == "__main__":
    main()
