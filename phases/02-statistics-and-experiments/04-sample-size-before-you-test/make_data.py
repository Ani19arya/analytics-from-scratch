"""Build data/pages.csv: synthetic baseline conversion rates and weekly traffic
for the pages a team wants to test. The data is synthetic.

weekly_visitors counts visits to the page in a typical week. Repeat visitors
are counted once per visit, so unique users per week are fewer.

Run: python3 make_data.py          (writes data/pages.csv for the default seed)
Use: build(seed) returns {"pages": rows} without writing anything.
"""
import csv
import os
import random

DEFAULT_SEED = 404
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "pages.csv")
PAGES = ["home", "search", "product", "cart", "checkout", "signup"]
FIELDS = ["page", "baseline_rate", "weekly_visitors"]


def build(seed=DEFAULT_SEED):
    """Return {"pages": rows}. The same seed always gives the same rows."""
    rng = random.Random(seed)
    rows = []
    for page in PAGES:
        rows.append({
            "page": page,
            "baseline_rate": round(rng.uniform(0.02, 0.40), 3),
            "weekly_visitors": rng.randrange(2000, 60000, 500),
        })
    return {"pages": rows}


def write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    rows = build()["pages"]
    write_csv(OUT, rows)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
