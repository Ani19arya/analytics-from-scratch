"""Build data/sales_long.csv: synthetic monthly revenue by region, one row per region and month.

West has no March row on purpose (the store was closed for a refit), so the wide
table has one empty cell.

    python3 make_data.py     # writes data/sales_long.csv for the default seed
    build(seed)              # returns {"sales_long": rows}, values as strings like the CSV
"""
import csv
import os
import random

DEFAULT_SEED = 502

REGIONS = ["North", "South", "East", "West"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]


def build(seed=DEFAULT_SEED):
    rng = random.Random(seed)
    rows = []
    for region in REGIONS:
        base = rng.randint(30, 60) * 1000
        for i, month in enumerate(MONTHS):
            if region == "West" and month == "Mar":
                continue
            rows.append({"region": region, "month": month, "revenue": str(base + i * rng.randint(500, 2500))})
    return {"sales_long": rows}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    rows = build()["sales_long"]
    with open(os.path.join(data, "sales_long.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["region", "month", "revenue"])
        w.writeheader()
        w.writerows(rows)
    print("wrote", len(rows), "rows")


if __name__ == "__main__":
    main()
