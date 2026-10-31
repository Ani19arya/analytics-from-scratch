"""Build data/postings.csv: synthetic analyst job postings with a posted pay range.

The data is synthetic. It is shaped like real pay data (most roles cluster,
a few senior roles pay far more), but no row is a real posting.

Run: python3 make_data.py          (writes data/postings.csv for the default seed)
Use: build(seed) returns {"postings": [row dicts]} without writing anything.
"""
import csv
import os
import random

DEFAULT_SEED = 2026
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "postings.csv")

TITLES = ["Data Analyst", "Business Analyst", "Product Analyst",
          "Marketing Analyst", "Financial Analyst"]
CITIES = ["Austin", "Chicago", "Denver", "Atlanta", "Seattle", "Boston"]
FIELDS = ["posting_id", "title", "city", "pay_min", "pay_max", "pay_mid"]


def build(seed=DEFAULT_SEED):
    """Return {"postings": rows}. The same seed always gives the same rows."""
    rng = random.Random(seed)
    rows = []
    for i in range(1, 301):
        title = rng.choice(TITLES)
        mid = rng.lognormvariate(11.3, 0.25)
        if i % 37 == 0:
            title = "Director of Analytics"
            mid = rng.uniform(230000, 320000)
        mid = round(mid / 1000) * 1000
        spread = round(mid * rng.uniform(0.10, 0.20) / 1000) * 1000
        rows.append({
            "posting_id": i,
            "title": title,
            "city": rng.choice(CITIES),
            "pay_min": mid - spread,
            "pay_max": mid + spread,
            "pay_mid": mid,
        })
    return {"postings": rows}


def write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    rows = build()["postings"]
    write_csv(OUT, rows)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
