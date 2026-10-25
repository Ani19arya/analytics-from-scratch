"""Build data/postings.csv: synthetic analyst job postings with a posted pay range.

The data is synthetic. It is shaped like real pay data (most roles cluster,
a few senior roles pay far more), but no row is a real posting.
Run: python3 make_data.py
"""
import csv
import os
import random

random.seed(2026)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "postings.csv")

TITLES = ["Data Analyst", "Business Analyst", "Product Analyst",
          "Marketing Analyst", "Financial Analyst"]
CITIES = ["Austin", "Chicago", "Denver", "Atlanta", "Seattle", "Boston"]


def main():
    rows = []
    for i in range(1, 301):
        title = random.choice(TITLES)
        mid = random.lognormvariate(11.3, 0.25)
        if i % 37 == 0:
            title = "Director of Analytics"
            mid = random.uniform(230000, 320000)
        mid = round(mid / 1000) * 1000
        spread = round(mid * random.uniform(0.10, 0.20) / 1000) * 1000
        rows.append({
            "posting_id": i,
            "title": title,
            "city": random.choice(CITIES),
            "pay_min": mid - spread,
            "pay_max": mid + spread,
            "pay_mid": mid,
        })
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
