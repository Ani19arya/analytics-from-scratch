"""Build the synthetic customers, orders and order_items tables for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/customers.csv, data/orders.csv and data/order_items.csv.
The data is synthetic and deterministic: the same seed always gives the same
rows. Tests call build(seed) for a second dataset.

On purpose, a few orders appear twice in orders.csv, as if an export ran twice
for them. Finding those repeats is part of the lesson.
"""
import csv
import datetime
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SEED = 3
FIRST_NAMES = ["Aarav", "Diya", "Kabir", "Meera", "Rohan", "Priya", "Ishaan", "Ananya", "Vikram", "Sara"]
INITIALS = ["K", "S", "M"]
CITIES = ["Mumbai", "Nagpur", "Nashik", "Pune"]
DISHES = {"veg thali": "180.00", "paneer roll": "120.00", "dal khichdi": "150.00",
          "chicken biryani": "260.00", "masala dosa": "110.00", "curd rice": "90.00"}


def build(seed=DEFAULT_SEED):
    """Return {"customers": [...], "orders": [...], "order_items": [...]}, every value as text."""
    rng = random.Random(seed)
    customers = []
    for i in range(1, rng.randint(22, 28) + 1):
        customers.append(
            {
                "customer_id": "C%03d" % i,
                "name": "%s %s." % (rng.choice(FIRST_NAMES), rng.choice(INITIALS)),
                "city": rng.choice(CITIES),
                "signup_date": (datetime.date(2026, 6, 1) + datetime.timedelta(days=rng.randint(0, 120))).isoformat(),
            }
        )
    orders, items = [], []
    for i in range(1, rng.randint(55, 65) + 1):
        order_id = str(7000 + i)
        orders.append(
            {
                "order_id": order_id,
                "customer_id": rng.choice(customers)["customer_id"],
                "order_date": (datetime.date(2026, 10, 1) + datetime.timedelta(days=rng.randint(0, 27))).isoformat(),
                "delivery_fee": rng.choice(["0.00", "25.00", "35.00", "49.00"]),
            }
        )
        for line in range(1, rng.choice([1, 1, 2, 2, 3, 4]) + 1):
            dish = rng.choice(sorted(DISHES))
            items.append(
                {
                    "order_id": order_id,
                    "line_no": str(line),
                    "dish": dish,
                    "quantity": str(rng.choice([1, 1, 1, 2, 3])),
                    "unit_price": DISHES[dish],
                }
            )
    # The export glitch: a few orders are written twice, as exact copies.
    for row in rng.sample(orders, rng.randint(2, 4)):
        orders.append(dict(row))
    orders.sort(key=lambda r: r["order_id"])
    return {"customers": customers, "orders": orders, "order_items": items}


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
