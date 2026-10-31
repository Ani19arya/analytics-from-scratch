"""Build data/products.csv and data/weekly_sales.csv for the Quernstone Hardware
restocking case.

The data is synthetic and deterministic (fixed seed). Quernstone Hardware is a
fictional hardware store. 12 weeks of sales, Monday 3 August to Sunday
25 October 2026, for 40 products, plus the stock on hand on 1 November 2026.

products.csv: sku, name, category, unit_cost, unit_price, on_hand (units in the
store on 1 November), lead_time_weeks (weeks from placing an order to the goods
arriving).

weekly_sales.csv: week_start, sku, units_sold, in_stock. in_stock is 1 when the
product was on the shelf all week and 0 when it ran out during the week, so
units_sold that week is lower than what customers wanted.

The story planted in the data:
- Six fast sellers are reordered in lots that are too small. They run out in
  about half the weeks, so their sales look lower than their demand.
- Six slow sellers were bought in bulk in the spring and have months of stock.
- One product ran out before August and was never restocked (no in-stock week).
- One product is new: it is in products.csv but has no sales rows yet.

    python3 make_data.py                        writes data/*.csv (seed 606)
    import make_data; make_data.build(seed=9)   returns the rows for another seed
"""
import csv
import datetime
import os
import random

SEED = 606
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
START = datetime.date(2026, 8, 3)
WEEKS = 12
PRODUCT_FIELDS = ["sku", "name", "category", "unit_cost", "unit_price", "on_hand", "lead_time_weeks"]
SALES_FIELDS = ["week_start", "sku", "units_sold", "in_stock"]

CATALOGUE = {
    "paint": ["Interior emulsion 5L", "Gloss white 750ml", "Masking tape 50m", "Paint roller set",
              "Wall filler 1kg", "Dust sheet", "Primer 2.5L", "Brush set"],
    "tools": ["Claw hammer", "Cordless drill", "Tape measure 8m", "Screwdriver set",
              "Spirit level 60cm", "Utility knife", "Hex key set", "Pliers"],
    "garden": ["Garden hose 30m", "Pruning shears", "Compost 50L", "Leaf rake",
               "Plant pots x10", "Weed killer 1L", "Garden gloves", "Watering can"],
    "plumbing": ["Silicone sealant", "PTFE tape", "Basin waste kit", "Tap washer pack",
                 "Push-fit elbow x5", "Sink plunger", "Shower head", "Drain unblocker"],
    "electrical": ["LED bulb B22 x4", "Extension lead 4-way", "Cable ties x100", "Fuse pack",
                   "Smart plug", "Light switch", "Torch LED", "Batteries AA x8"],
}


def poisson(rng, lam):
    """Knuth's method: fine for the small weekly means used here."""
    limit = pow(2.718281828459045, -lam)
    k, p = 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def build(seed=SEED):
    """Return {"products": [...], "weekly_sales": [...]}, rows as dicts of text values."""
    rng = random.Random(seed)
    names = [(cat, name) for cat in CATALOGUE for name in CATALOGUE[cat]]
    order = list(range(len(names)))
    rng.shuffle(order)
    kinds = {}
    for i in order[:6]:
        kinds[i] = "starved"
    for i in order[6:12]:
        kinds[i] = "bulk"
    kinds[order[12]] = "dead"
    kinds[order[13]] = "new"
    products, sales = [], []
    for i, (cat, name) in enumerate(names):
        sku = "Q%03d" % (101 + i)
        kind = kinds.get(i, "normal")
        price = round(rng.uniform(3, 60), 2)
        cost = round(price * rng.uniform(0.45, 0.70), 2)
        lead = rng.choice((1, 1, 2, 2, 3))
        if kind == "starved":
            lam = rng.uniform(14, 26)
        elif kind == "bulk":
            lam = rng.uniform(0.8, 3.0)
        else:
            lam = rng.uniform(3, 14)
        last_rate = None
        if kind != "new":
            for w in range(WEEKS):
                demand = poisson(rng, lam)
                in_stock = 1
                sold = demand
                if kind == "dead":
                    in_stock, sold = 0, 0
                elif kind == "starved" and rng.random() < 0.5:
                    in_stock = 0
                    sold = int(demand * rng.uniform(0.15, 0.6))
                elif kind == "normal" and rng.random() < 0.06:
                    in_stock = 0
                    sold = int(demand * rng.uniform(0.5, 0.9))
                sales.append({
                    "week_start": (START + datetime.timedelta(weeks=w)).isoformat(),
                    "sku": sku, "units_sold": str(sold), "in_stock": str(in_stock),
                })
            last_rate = lam
        if kind == "starved":
            on_hand = rng.randint(0, 6)
        elif kind == "bulk":
            on_hand = int(lam * rng.uniform(25, 60))
        elif kind == "dead":
            on_hand = 0
        elif kind == "new":
            on_hand = rng.randint(20, 40)
        else:
            on_hand = int(last_rate * rng.uniform(4, 10))
        products.append({
            "sku": sku, "name": name, "category": cat, "unit_cost": "%.2f" % cost,
            "unit_price": "%.2f" % price, "on_hand": str(on_hand), "lead_time_weeks": str(lead),
        })
    return {"products": products, "weekly_sales": sales}


def write_csv(rows, fields, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    data = build()
    write_csv(data["products"], PRODUCT_FIELDS, os.path.join(DATA, "products.csv"))
    write_csv(data["weekly_sales"], SALES_FIELDS, os.path.join(DATA, "weekly_sales.csv"))
    print("wrote", len(data["products"]), "products and", len(data["weekly_sales"]), "sales rows to", DATA)


if __name__ == "__main__":
    main()
