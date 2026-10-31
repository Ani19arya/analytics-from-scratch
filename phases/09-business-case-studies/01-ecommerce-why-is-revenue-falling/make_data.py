"""Build the data for the Wrenloom revenue case.

Wrenloom is a fictional online shop for home textiles (bedsheets, towels,
curtains). Two files cover 1 April to 30 September 2026 (Q2 and Q3 2026).
The data is synthetic and deterministic (fixed seed).

data/sessions.csv  one row per day and channel: date, channel, sessions.
data/orders.csv    one row per order: order_id, order_date, channel, items,
                   revenue (rupees, after discounts).

Channels: search (paid and organic search), social (paid social ads) and
email. The story planted in the data: in Q3 the marketing team moved budget
from search ads to social ads. Search sessions fall, social sessions almost
triple, and total sessions go up. Within each channel the conversion rate and
the basket size do not change at all between the quarters. Social visitors
convert far less often and buy smaller baskets, so the shift in the channel
mix is what pulls revenue down. A new checkout page launched on 15 July is a
red herring: it changes nothing.

    python3 make_data.py                        writes both CSVs (seed 904)
    import make_data; make_data.build(seed=5)   returns the rows for another seed
"""
import csv
import datetime
import os
import random

SEED = 904
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
START = datetime.date(2026, 4, 1)
END = datetime.date(2026, 9, 30)
Q3_START = datetime.date(2026, 7, 1)
SESSION_FIELDS = ["date", "channel", "sessions"]
ORDER_FIELDS = ["order_id", "order_date", "channel", "items", "revenue"]
# mean daily sessions in Q2 and Q3, conversion rate, mean items, mean price per item
CHANNELS = {
    "search": {"q2": 190, "q3": 152, "conv": 0.030, "items": 2.2, "price": 1000},
    "social": {"q2": 45, "q3": 125, "conv": 0.008, "items": 1.4, "price": 1050},
    "email": {"q2": 60, "q3": 60, "conv": 0.040, "items": 1.8, "price": 1000},
}


def build(seed=SEED):
    """Return {"sessions": [row, ...], "orders": [row, ...]}, each row a dict of text values."""
    rng = random.Random(seed)
    sessions = []
    orders = []
    n = 0
    day = START
    while day <= END:
        q = "q3" if day >= Q3_START else "q2"
        weekend = day.weekday() >= 5
        for channel in ("search", "social", "email"):
            c = CHANNELS[channel]
            mean = c[q] * (1.15 if weekend else 1.0)
            s = max(0, int(round(rng.gauss(mean, mean * 0.12))))
            sessions.append({"date": day.isoformat(), "channel": channel, "sessions": str(s)})
            buyers = sum(1 for _ in range(s) if rng.random() < c["conv"])
            for _ in range(buyers):
                n += 1
                items = 1
                while rng.random() < 1 - 1 / c["items"]:
                    items += 1
                revenue = sum(rng.randint(int(c["price"] * 0.5), int(c["price"] * 1.5)) for _ in range(items))
                orders.append({"order_id": "W%05d" % n, "order_date": day.isoformat(), "channel": channel,
                               "items": str(items), "revenue": str(revenue)})
        day += datetime.timedelta(days=1)
    return {"sessions": sessions, "orders": orders}


def write_csv(rows, fields, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_all(data, folder):
    write_csv(data["sessions"], SESSION_FIELDS, os.path.join(folder, "sessions.csv"))
    write_csv(data["orders"], ORDER_FIELDS, os.path.join(folder, "orders.csv"))


def main():
    data = build()
    write_all(data, DATA)
    print("wrote", len(data["sessions"]), "session rows and", len(data["orders"]), "orders to", DATA)


if __name__ == "__main__":
    main()
