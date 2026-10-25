"""Build data/daily_channels.csv: one row per day and traffic channel for a
synthetic online shop over two weeks (5 to 18 October 2026).

Columns: date, channel, visitors, orders, revenue.
The data is synthetic and deterministic (fixed seed). In the second week the
paid_social landing page converts worse, which is the story the lesson finds.
Run from the lesson folder: python3 make_data.py
"""
import csv
import datetime
import os
import random

random.seed(31)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "daily_channels.csv")
START = datetime.date(2026, 10, 5)
SPLIT = datetime.date(2026, 10, 12)

# channel: (daily visitors, conversion rate, mean order value)
PRIOR = {"search": (1200, 0.032, 58.0), "email": (420, 0.050, 64.0), "paid_social": (900, 0.028, 52.0)}
CURRENT = {"search": (1180, 0.032, 58.0), "email": (430, 0.050, 64.0), "paid_social": (980, 0.013, 52.0)}


def main():
    rows = []
    for offset in range(14):
        day = START + datetime.timedelta(days=offset)
        params = PRIOR if day < SPLIT else CURRENT
        for channel in ("search", "email", "paid_social"):
            base, rate, aov = params[channel]
            visitors = max(1, int(round(base * random.gauss(1.0, 0.06))))
            orders = sum(1 for _ in range(visitors) if random.random() < rate)
            revenue = sum(max(5.0, random.gauss(aov, 15.0)) for _ in range(orders))
            rows.append({
                "date": day.isoformat(),
                "channel": channel,
                "visitors": visitors,
                "orders": orders,
                "revenue": "%.2f" % revenue,
            })
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "channel", "visitors", "orders", "revenue"])
        w.writeheader()
        w.writerows(rows)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
