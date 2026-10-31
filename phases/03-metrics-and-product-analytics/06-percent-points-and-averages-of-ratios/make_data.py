"""Build data/daily.csv: daily course page visits and orders for the fictional
online course shop Learnhaven, 1 September to 31 October 2026 (synthetic).

Columns: date, visits (visits to course pages that day; one person can make
several visits, so visits add up across days but people would not), orders
(orders placed that day). Weekdays bring more visits than weekends, weekend
visits convert better, and a three-day influencer campaign in October brings
very many visits that rarely end in an order.
The data is synthetic and deterministic (fixed seed).

Run: python3 make_data.py          (writes data/daily.csv for the default seed)
Use: build(seed) returns {"daily": [row dicts]} without writing anything.
"""
import csv
import datetime
import os
import random

DEFAULT_SEED = 59
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "daily.csv")
FIELDS = ["date", "visits", "orders"]
FIRST, LAST = datetime.date(2026, 9, 1), datetime.date(2026, 10, 31)
CAMPAIGN = (datetime.date(2026, 10, 14), datetime.date(2026, 10, 16))


def build(seed=DEFAULT_SEED):
    """Return {"daily": rows}. The same seed always gives the same rows."""
    rng = random.Random(seed)
    rows = []
    day = FIRST
    while day <= LAST:
        if CAMPAIGN[0] <= day <= CAMPAIGN[1]:
            visits, rate = rng.randint(5200, 6800), 0.009
        elif day.weekday() >= 5:
            visits, rate = rng.randint(380, 560), 0.036 if day.month == 9 else 0.037
        else:
            visits, rate = rng.randint(950, 1250), 0.024 if day.month == 9 else 0.0245
        orders = sum(1 for _ in range(visits) if rng.random() < rate)
        rows.append({"date": day.isoformat(), "visits": visits, "orders": orders})
        day += datetime.timedelta(days=1)
    return {"daily": rows}


def write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    rows = build()["daily"]
    write_csv(OUT, rows)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
