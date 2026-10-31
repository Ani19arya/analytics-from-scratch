"""Build the synthetic sales table for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/orders.csv: every Tiffinbell order from Monday 19 October 2026
to Thursday 29 October 2026. The data is synthetic and deterministic: the same
seed always gives the same rows. Tests call build(seed) for a second dataset.

In every seed one city has fewer orders in the current week (26 to 29 October).
Which city that is depends on the seed.
"""
import csv
import datetime
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SEED = 87
CITIES = ["Mumbai", "Nagpur", "Nashik", "Pune"]
FIRST_DAY = datetime.date(2026, 10, 19)
LAST_DAY = datetime.date(2026, 10, 29)
CURRENT_WEEK_START = datetime.date(2026, 10, 26)


def build(seed=DEFAULT_SEED):
    """Return {"orders": [rows]} where every value is text, exactly as in the CSV."""
    rng = random.Random(seed)
    slow_city = rng.choice(CITIES)
    rows = []
    day = FIRST_DAY
    while day <= LAST_DAY:
        weekend = day.weekday() >= 5
        for city in CITIES:
            n = rng.randint(8, 14)
            if weekend:
                n = n + rng.randint(3, 6)
            if city == slow_city and day >= CURRENT_WEEK_START:
                n = rng.randint(3, 7)
            for _ in range(n):
                rows.append(
                    {
                        "order_date": day.isoformat(),
                        "city": city,
                        "channel": "app" if rng.random() < 0.7 else "web",
                        "status": "cancelled" if rng.random() < 0.07 else "completed",
                        "amount": "%.2f" % rng.uniform(150, 900),
                    }
                )
        day += datetime.timedelta(days=1)
    for i, row in enumerate(rows, 1):
        row["order_id"] = str(50000 + i)
    columns = ["order_id", "order_date", "city", "channel", "status", "amount"]
    return {"orders": [{c: r[c] for c in columns} for r in rows]}


def main():
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    for name, rows in build().items():
        with open(os.path.join(HERE, "data", name + ".csv"), "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print("wrote %d rows to data/%s.csv" % (len(rows), name))


if __name__ == "__main__":
    main()
