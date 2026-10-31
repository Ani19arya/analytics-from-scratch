"""Build data/orders.csv for the Tiffinbell cancellations case.

One row per order placed from Monday 3 August to Sunday 25 October 2026
(12 weeks) in four cities. The data is synthetic and deterministic (fixed seed).

Columns: order_id, order_date, city, restaurant_id, app_version, status,
cancel_reason (blank when the order was delivered; otherwise restaurant,
rider or customer: who pressed cancel).

The story planted in the data: from week 7 the new app release 7.4.0 rolls out
in Nagpur only (a staged rollout). On 7.4.0 the order confirmation screen
sometimes never loads, and many of those customers cancel. The cancel is
logged as reason "customer". Every other city and version keeps the same
cancel rates all twelve weeks.

    python3 make_data.py                        writes data/orders.csv (seed 409)
    import make_data; make_data.build(seed=7)   returns the rows for another seed
"""
import csv
import datetime
import os
import random

SEED = 409
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "orders.csv")
START = datetime.date(2026, 8, 3)
DAYS = 84
CITIES = (("Pune", 0.30), ("Mumbai", 0.30), ("Nagpur", 0.20), ("Nashik", 0.20))
FIELDS = ["order_id", "order_date", "city", "restaurant_id", "app_version", "status", "cancel_reason"]
# share of Nagpur orders placed on 7.4.0 in weeks 7 to 12
ROLLOUT = {7: 0.35, 8: 0.60, 9: 0.75, 10: 0.85, 11: 0.90, 12: 0.95}
BASE = {"restaurant": 0.020, "rider": 0.015, "customer": 0.015}


def build(seed=SEED):
    """Return {"orders": [row, ...]}, each row a dict of text values as written to the CSV."""
    rng = random.Random(seed)
    rows = []
    n = 0
    for offset in range(DAYS):
        day = START + datetime.timedelta(days=offset)
        week = offset // 7 + 1
        for _ in range(int(round(rng.gauss(22, 3)))):
            n += 1
            r = rng.random()
            acc = 0.0
            for city, share in CITIES:
                acc += share
                if r < acc:
                    break
            ci = [c for c, _ in CITIES].index(city)
            restaurant = "R%02d" % (ci * 10 + rng.randint(1, 10))
            if city == "Nagpur" and rng.random() < ROLLOUT.get(week, 0.0):
                version = "7.4.0"
            else:
                version = "7.2.5" if rng.random() < 0.10 else "7.3.2"
            probs = dict(BASE)
            if version == "7.4.0":
                probs["customer"] = 0.35
            reason = ""
            u = rng.random()
            acc = 0.0
            for key in ("restaurant", "rider", "customer"):
                acc += probs[key]
                if u < acc:
                    reason = key
                    break
            rows.append({
                "order_id": "T%05d" % n,
                "order_date": day.isoformat(),
                "city": city,
                "restaurant_id": restaurant,
                "app_version": version,
                "status": "cancelled" if reason else "delivered",
                "cancel_reason": reason,
            })
    return {"orders": rows}


def write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    rows = build()["orders"]
    write_csv(rows, OUT)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
