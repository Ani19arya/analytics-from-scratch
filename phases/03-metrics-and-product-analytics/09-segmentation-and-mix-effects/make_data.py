"""Build data/daily_devices.csv: one row per day and device for a synthetic
online shop, 1 September to 31 October 2026.

Columns: date, device, sessions, orders.
The data is synthetic and deterministic (fixed seed). In October a paid social
campaign sends much more mobile traffic. Each device converts about as well as
before, but mobile converts far less than desktop, so the total rate falls.

    python3 make_data.py          writes data/daily_devices.csv (seed 19)
    import make_data; make_data.build(seed=4)   returns the rows for another seed
"""
import csv
import datetime
import os
import random

SEED = 19
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "daily_devices.csv")
START = datetime.date(2026, 9, 1)
SPLIT = datetime.date(2026, 10, 1)
END = datetime.date(2026, 10, 31)
DEVICES = ("desktop", "mobile", "tablet")
FIELDS = ["date", "device", "sessions", "orders"]

# device: (daily sessions, conversion rate)
SEPT = {"desktop": (520, 0.036), "mobile": (470, 0.014), "tablet": (90, 0.025)}
OCT = {"desktop": (510, 0.037), "mobile": (900, 0.0152), "tablet": (85, 0.026)}


def build(seed=SEED):
    """Return {"daily_devices": [row, ...]}, each row a dict of text values."""
    rng = random.Random(seed)
    rows = []
    day = START
    while day <= END:
        params = SEPT if day < SPLIT else OCT
        weekend = 0.8 if day.weekday() >= 5 else 1.0
        for device in DEVICES:
            base, rate = params[device]
            sessions = max(0, int(round(base * weekend * rng.gauss(1.0, 0.08))))
            orders = sum(1 for _ in range(sessions) if rng.random() < rate)
            rows.append({"date": day.isoformat(), "device": device,
                         "sessions": str(sessions), "orders": str(orders)})
        day += datetime.timedelta(days=1)
    return {"daily_devices": rows}


def write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    rows = build()["daily_devices"]
    write_csv(rows, OUT)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
