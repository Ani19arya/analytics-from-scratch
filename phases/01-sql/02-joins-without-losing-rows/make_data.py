"""Build the synthetic customers, orders and addresses tables for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/customers.csv, data/orders.csv and data/customer_addresses.csv.
The data is synthetic and deterministic (fixed seed).
"""
import csv
import datetime
import os
import random

random.seed(202)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CITIES = ["Austin", "Denver", "Pune", "Leeds", "Perth"]


def write(name, rows):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/%s" % (len(rows), name))


def main():
    os.makedirs(DATA, exist_ok=True)
    start = datetime.date(2026, 1, 1)
    customers, addresses = [], []
    for i in range(1, 121):
        cid = "C%03d" % i
        customers.append(
            {
                "customer_id": cid,
                "signup_date": (start + datetime.timedelta(days=random.randint(0, 180))).isoformat(),
            }
        )
        home = random.choice(CITIES)
        addresses.append({"customer_id": cid, "city": home, "is_primary": 1})
        # About a third of customers also saved a second, non-primary address.
        if random.random() < 0.33:
            other = random.choice([c for c in CITIES if c != home])
            addresses.append({"customer_id": cid, "city": other, "is_primary": 0})

    # Only some customers ever order. The rest exist but have no orders.
    buyers = random.sample([c["customer_id"] for c in customers], 94)
    orders = []
    for order_id in range(1, 361):
        orders.append(
            {
                "order_id": order_id,
                "customer_id": random.choice(buyers),
                "amount": "%.2f" % random.uniform(10, 150),
            }
        )
    write("customers.csv", customers)
    write("orders.csv", orders)
    write("customer_addresses.csv", addresses)


if __name__ == "__main__":
    main()
