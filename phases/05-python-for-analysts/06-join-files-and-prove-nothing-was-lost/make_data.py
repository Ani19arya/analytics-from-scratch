"""Build two synthetic Kestrel Home files that have to be joined.

Run from the lesson folder: python3 make_data.py
Writes:
  data/order_lines.csv   October 2026 order lines from the US shop, one row per line
  data/products.csv      the product catalogue: sku, product name, category
The data is synthetic and deterministic (fixed seed).

The traps are added on purpose:
- the catalogue lists one product twice, word for word (a copy and paste);
- it lists another product twice with two different categories;
- three products sold in October are not in the catalogue yet;
- a few products in the catalogue sold nothing in October;
- delivery fees are order lines with no sku at all.

The test calls build(seed=...) with another seed to get a second dataset in memory.
"""
import csv
import os
import random

DEFAULT_SEED = 506
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CATEGORIES = {"Sofas": (450, 1600), "Tables": (180, 900), "Lighting": (35, 260), "Rugs": (60, 480),
              "Decor": (12, 140), "Storage": (90, 620)}
WORDS = ["Alder", "Brook", "Cove", "Drift", "Ember", "Fable", "Grove", "Haven", "Isle", "Juno", "Knoll", "Loom"]
LINE_FIELDS = ["line_id", "order_id", "sku", "qty", "amount"]
PRODUCT_FIELDS = ["sku", "product_name", "category"]


def build(seed=DEFAULT_SEED):
    """Return {"order_lines": rows, "products": rows}, every cell as text, like csv.DictReader."""
    rng = random.Random(seed)
    cats = sorted(CATEGORIES)
    n_products = rng.randint(38, 44)
    products, price = [], {}
    for i in range(n_products):
        cat = cats[i % len(cats)]
        sku = "KH-%04d" % (1000 + i * 7)
        low, high = CATEGORIES[cat]
        price[sku] = round(rng.uniform(low, high), 0) - 0.01
        products.append({"sku": sku, "product_name": "%s %s" % (rng.choice(WORDS), cat[:-1] if cat.endswith("s") else cat),
                         "category": cat})
    sold = list(price)
    never_sold = set(rng.sample(sold[:-3], rng.randint(3, 6)))
    missing = sold[-3:]                         # sold in October, not in the catalogue yet
    sellable = [s for s in sold if s not in never_sold]
    catalogue = [p for p in products if p["sku"] not in missing]

    copied = rng.choice([p for p in catalogue if p["sku"] not in never_sold])
    conflict = rng.choice([p for p in catalogue if p["sku"] not in never_sold and p is not copied])
    other_cat = rng.choice([c for c in cats if c != conflict["category"]])
    catalogue.insert(catalogue.index(copied) + 1, dict(copied))
    catalogue.append(dict(conflict, category=other_cat))

    lines, line_id = [], 1
    for order in range(rng.randint(210, 250)):
        order_id = "KO-%05d" % (40001 + order)
        for _ in range(rng.choice([1, 1, 1, 2, 2, 3])):
            sku = rng.choice(sellable)
            qty = rng.choice([1, 1, 1, 2, 4])
            lines.append({"line_id": str(line_id), "order_id": order_id, "sku": sku, "qty": str(qty),
                          "amount": "%.2f" % (qty * price[sku])})
            line_id += 1
        if rng.random() < 0.04:
            lines.append({"line_id": str(line_id), "order_id": order_id, "sku": "", "qty": "1", "amount": "49.00"})
            line_id += 1
    # Make sure the copied, the conflicting and every missing product actually sold.
    for i, sku in enumerate([copied["sku"], conflict["sku"]] + missing):
        lines[i * 3]["sku"] = sku
        lines[i * 3]["amount"] = "%.2f" % (int(lines[i * 3]["qty"]) * price[sku])
    return {"order_lines": lines, "products": catalogue}


def main():
    os.makedirs(DATA, exist_ok=True)
    data = build()
    for name, fields in (("order_lines", LINE_FIELDS), ("products", PRODUCT_FIELDS)):
        with open(os.path.join(DATA, name + ".csv"), "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(data[name])
        print("wrote %d rows to data/%s.csv" % (len(data[name]), name))


if __name__ == "__main__":
    main()
