"""Build data/daily_channels.csv: one row per day and traffic channel for a
synthetic online shop over two weeks (5 to 18 October 2026).

Columns: date, channel, visitors, orders, revenue.
The data is synthetic and deterministic (fixed seed). In the second week the
paid_social landing page converts worse, which is the story the lesson finds.

    python3 make_data.py          writes data/daily_channels.csv (seed 31)
    import make_data; make_data.build(seed=7)   returns the rows for another seed
"""
import csv
import datetime
import os
import random

SEED = 31
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "daily_channels.csv")
START = datetime.date(2026, 10, 5)
SPLIT = datetime.date(2026, 10, 12)
CHANNELS = ("search", "email", "paid_social")
FIELDS = ["date", "channel", "visitors", "orders", "revenue"]

# channel: (daily visitors, conversion rate, mean order value)
PRIOR = {"search": (1200, 0.032, 58.0), "email": (420, 0.050, 64.0), "paid_social": (900, 0.028, 52.0)}
CURRENT = {"search": (1180, 0.032, 58.0), "email": (430, 0.050, 64.0), "paid_social": (980, 0.013, 52.0)}


def build(seed=SEED):
    """Return {"daily_channels": [row, ...]}. Each row is a dict of text values,
    exactly as they are written to the CSV."""
    rng = random.Random(seed)
    rows = []
    for offset in range(14):
        day = START + datetime.timedelta(days=offset)
        params = PRIOR if day < SPLIT else CURRENT
        for channel in CHANNELS:
            base, rate, aov = params[channel]
            visitors = max(1, int(round(base * rng.gauss(1.0, 0.06))))
            orders = sum(1 for _ in range(visitors) if rng.random() < rate)
            revenue = sum(max(5.0, rng.gauss(aov, 15.0)) for _ in range(orders))
            rows.append({
                "date": day.isoformat(),
                "channel": channel,
                "visitors": str(visitors),
                "orders": str(orders),
                "revenue": "%.2f" % revenue,
            })
    return {"daily_channels": rows}


def write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    rows = build()["daily_channels"]
    write_csv(rows, OUT)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
