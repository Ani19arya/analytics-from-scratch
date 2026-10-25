"""Build data/pages.csv: synthetic baseline conversion rates and weekly traffic
for the pages a team wants to test. The data is synthetic.
Run: python3 make_data.py
"""
import csv
import os
import random

random.seed(404)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "pages.csv")
PAGES = ["home", "search", "product", "cart", "checkout", "signup"]


def main():
    rows = []
    for page in PAGES:
        rows.append({
            "page": page,
            "baseline_rate": round(random.uniform(0.02, 0.40), 3),
            "weekly_visitors": random.randrange(2000, 60000, 500),
        })
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["page", "baseline_rate", "weekly_visitors"])
        w.writeheader()
        w.writerows(rows)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
