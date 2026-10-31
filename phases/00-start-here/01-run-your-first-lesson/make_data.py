"""Build the synthetic orders table for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/orders.csv. The data is synthetic and deterministic: the same seed
always gives the same rows. Tests call build(seed) to get a second dataset.
"""
import csv
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SEED = 1
DISHES = ["veg thali", "paneer roll", "dal khichdi", "chicken biryani", "masala dosa", "curd rice"]


def build(seed=DEFAULT_SEED):
    """Return {"orders": [rows]} where every value is text, exactly as in the CSV."""
    rng = random.Random(seed)
    n = rng.randint(36, 44)
    orders = []
    for i in range(1, n + 1):
        orders.append(
            {
                "order_id": str(1000 + i),
                "dish": rng.choice(DISHES),
                # About 1 order in 20 is a free replacement meal, so its amount is 0.00.
                "amount": "%.2f" % (0.0 if rng.random() < 0.05 else rng.uniform(90, 480)),
            }
        )
    return {"orders": orders}


def main():
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    for name, rows in build().items():
        with open(os.path.join(HERE, "data", name + ".csv"), "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print("wrote %d rows to data/%s.csv" % (len(rows), name))


if __name__ == "__main__":
    main()
