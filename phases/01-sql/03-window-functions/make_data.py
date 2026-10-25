"""Build the synthetic monthly revenue and sales rep tables for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/monthly_revenue.csv and data/rep_sales.csv.
The data is synthetic and deterministic (fixed seed).
"""
import csv
import os
import random

random.seed(303)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
REGIONS = {"North": 42000, "South": 35000, "West": 51000}
MONTHS = ["2025-10", "2025-11", "2025-12"] + ["2026-%02d" % m for m in range(1, 10)]


def write(name, rows):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/%s" % (len(rows), name))


def main():
    os.makedirs(DATA, exist_ok=True)
    revenue = []
    for region, level in REGIONS.items():
        for month in MONTHS:
            level = max(5000, level + random.randint(-6000, 7000))
            revenue.append({"region": region, "month": month, "revenue": level})

    reps = []
    n = 1
    for region in REGIONS:
        for _ in range(5):
            # Sales rounded to the nearest 5,000 so that ties happen naturally.
            reps.append({"rep": "R%02d" % n, "region": region, "sales": 5000 * random.randint(10, 16)})
            n += 1
    # Force a tie at the top of North so RANK and ROW_NUMBER visibly differ.
    north = [r for r in reps if r["region"] == "North"]
    top = max(r["sales"] for r in north)
    north[-1]["sales"] = top
    write("monthly_revenue.csv", revenue)
    write("rep_sales.csv", reps)


if __name__ == "__main__":
    main()
