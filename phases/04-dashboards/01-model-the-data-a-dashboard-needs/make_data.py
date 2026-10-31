"""Build the synthetic raw transactions table for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/transactions.csv: one row per order line, the way an
order system exports it, with product and region details repeated on
every line. The data is synthetic and deterministic (fixed seed).

The test calls build(seed=...) with another seed to get a second,
different dataset in memory, so a query that hard-codes the answers fails.
"""
import csv
import datetime
import os
import random

DEFAULT_SEED = 401

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

PRODUCTS = [
    ("Desk Lamp", "Lighting", 34.50),
    ("Floor Lamp", "Lighting", 89.00),
    ("Pendant Light", "Lighting", 120.00),
    ("Oak Shelf", "Storage", 64.00),
    ("Wire Basket", "Storage", 12.75),
    ("Linen Cushion", "Textiles", 22.00),
    ("Wool Throw", "Textiles", 58.00),
    ("Cotton Rug", "Textiles", 140.00),
    ("Wall Clock", "Decor", 41.25),
    ("Ceramic Vase", "Decor", 27.50),
]
REGIONS = [("North", "Amara Osei"), ("South", "Diego Ramos"), ("East", "Mei Lin"), ("West", "Tom Becker")]


def build(seed=DEFAULT_SEED):
    """Return {"transactions": [row, ...]} with values as they appear in the CSV."""
    rng = random.Random(seed)
    rows = []
    order_id = 10000
    day = datetime.date(2025, 1, 1)
    end = datetime.date(2025, 12, 31)
    while day <= end:
        # The warehouse does not ship on Sundays, and orders are dated by ship
        # date, so Sundays have no rows at all.
        if day.weekday() != 6:
            for _ in range(rng.randint(1, 3)):
                order_id += 1
                region, manager = rng.choice(REGIONS)
                for line_no in range(1, rng.randint(1, 3) + 1):
                    product, category, price = rng.choice(PRODUCTS)
                    rows.append({
                        "order_id": order_id,
                        "line_no": line_no,
                        "order_date": day.isoformat(),
                        "product": product,
                        "category": category,
                        "unit_price": "%.2f" % price,
                        "region": region,
                        "region_manager": manager,
                        "quantity": rng.randint(1, 4),
                    })
        day += datetime.timedelta(days=1)
    return {"transactions": rows}


def main():
    os.makedirs(DATA, exist_ok=True)
    rows = build()["transactions"]
    with open(os.path.join(DATA, "transactions.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/transactions.csv" % len(rows))


if __name__ == "__main__":
    main()
