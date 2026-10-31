"""Build the synthetic orders table for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/orders.csv. The data is synthetic and deterministic (fixed seed).

build(seed) returns the rows without writing anything. The test calls it with
a second seed to check your queries on data you have not seen.
"""
import csv
import datetime
import os
import random

SEED = 101
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "orders.csv")

# Cities get different weights so the group sizes differ.
CITIES = [("Austin", 5), ("Denver", 4), ("Pune", 3), ("Leeds", 2), ("Perth", 1)]
STATUSES = [("completed", 85), ("refunded", 10), ("cancelled", 5)]


def pick(rng, weighted):
    names = [w[0] for w in weighted]
    weights = [w[1] for w in weighted]
    return rng.choices(names, weights=weights, k=1)[0]


def build(seed=SEED):
    """Return {"orders": [row, ...]}. Each row is a dict, values as written to the CSV."""
    rng = random.Random(seed)
    start = datetime.date(2026, 7, 1)
    rows = []
    for order_id in range(1, 401):
        day = start + datetime.timedelta(days=rng.randint(0, 91))
        rows.append(
            {
                "order_id": order_id,
                "customer_id": "C%03d" % rng.randint(1, 150),
                "city": pick(rng, CITIES),
                "order_date": day.isoformat(),
                "amount": "%.2f" % rng.uniform(8, 180),
                "status": pick(rng, STATUSES),
            }
        )
    return {"orders": rows}


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    rows = build()["orders"]
    with open(OUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to %s" % (len(rows), OUT))


if __name__ == "__main__":
    main()
