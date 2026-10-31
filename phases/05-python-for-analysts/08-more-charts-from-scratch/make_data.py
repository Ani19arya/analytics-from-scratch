"""Build data/deliveries.csv: four weeks of synthetic Tiffinbell deliveries.

Two kinds of delivery are mixed together on purpose: short trips from a nearby kitchen
(about 22 minutes) and long trips across town (about 46 minutes, all over 5 km). A
histogram with wide bins hides the two groups; narrow bins show them.

    python3 make_data.py     # writes data/deliveries.csv for the default seed
    build(seed)              # returns {"deliveries": rows}, values as strings like the CSV
"""
import csv
import os
import random
from datetime import date, timedelta

DEFAULT_SEED = 508
START = date(2026, 9, 28)   # a Monday
DAYS = 28
CITIES = ["Pune", "Mumbai", "Nashik", "Nagpur"]
FIELDS = ["delivery_id", "order_date", "city", "distance_km", "minutes"]


def build(seed=DEFAULT_SEED, far_share=0.4):
    rng = random.Random(seed)
    rows, n = [], 0
    for day in range(DAYS):
        d = START + timedelta(days=day)
        weekend = d.weekday() >= 5
        for _ in range(rng.randint(36, 46) if weekend else rng.randint(24, 34)):
            n += 1
            if rng.random() < far_share:
                km = rng.uniform(5.2, 9.5)
                minutes = rng.gauss(46, 5)
            else:
                km = rng.uniform(0.6, 4.2)
                minutes = rng.gauss(22, 4)
            rows.append({"delivery_id": "D%04d" % n, "order_date": d.isoformat(),
                         "city": rng.choice(CITIES), "distance_km": "%.1f" % km,
                         "minutes": "%.1f" % max(8.0, minutes)})
    return {"deliveries": rows}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(here, "data"), exist_ok=True)
    rows = build()["deliveries"]
    with open(os.path.join(here, "data", "deliveries.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print("wrote", len(rows), "deliveries")


if __name__ == "__main__":
    main()
