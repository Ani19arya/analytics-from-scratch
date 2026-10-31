"""Build data/touchpoints.csv and data/conversions.csv for a synthetic online
course shop: marketing touches from 1 August to 31 October 2026, and first purchases
in September and October 2026.

touchpoints.csv: user_id, touch_time, channel   (time as 'YYYY-MM-DD HH:MM')
conversions.csv: user_id, conversion_time, revenue

The data is synthetic and deterministic (fixed seed). Paid social mostly starts
journeys (people discover a course from an ad), search sits in the middle, and email
mostly closes them (a reminder before purchase). Some touches happen after the purchase
or more than 30 days before it, a few buyers have no tracked touch at all, and some
users never buy. At most one purchase per user.

    python3 make_data.py          writes both files (seed 61)
    import make_data; make_data.build(seed=9)   returns the rows for another seed
"""
import csv
import datetime
import os
import random

SEED = 61
HERE = os.path.dirname(os.path.abspath(__file__))
FIELDS = {"touchpoints": ["user_id", "touch_time", "channel"],
          "conversions": ["user_id", "conversion_time", "revenue"]}
FIRST = datetime.datetime(2026, 8, 1)
LAST = datetime.datetime(2026, 10, 31, 23, 59)
# channel weights for the first touch, middle touches and the last touch before buying
OPENERS = {"paid_social": 0.55, "search": 0.25, "affiliate": 0.15, "email": 0.05}
MIDDLE = {"search": 0.40, "paid_social": 0.25, "email": 0.25, "affiliate": 0.10}
CLOSERS = {"email": 0.55, "search": 0.30, "affiliate": 0.10, "paid_social": 0.05}
PRICES = (29.0, 49.0, 79.0, 129.0)


def pick(rng, weights):
    x = rng.random() * sum(weights.values())
    for name in sorted(weights):
        x -= weights[name]
        if x < 0:
            return name
    return sorted(weights)[-1]


def stamp(t):
    return t.strftime("%Y-%m-%d %H:%M")


def build(seed=SEED):
    """Return {"touchpoints": [...], "conversions": [...]}, rows of text values."""
    rng = random.Random(seed)
    touches, conversions = [], []
    for uid in range(1, 461):
        user = "u%03d" % uid
        start = FIRST + datetime.timedelta(minutes=rng.randint(0, 80 * 24 * 60))
        n = rng.choice((1, 1, 2, 2, 3, 3, 4, 5))
        times = [start]
        for _ in range(n - 1):
            times.append(times[-1] + datetime.timedelta(minutes=int(rng.expovariate(1 / (4.0 * 24 * 60)))))
        channels = [pick(rng, OPENERS)] + [pick(rng, MIDDLE) for _ in range(n - 2)]
        if n > 1:
            channels.append(pick(rng, CLOSERS))
        buys = rng.random() < 0.45
        conv = times[-1] + datetime.timedelta(minutes=rng.randint(5, 3 * 24 * 60))
        if rng.random() < 0.06:   # an old touch from long before the journey
            old = conv - datetime.timedelta(days=rng.randint(31, 60))
            times.insert(0, old)
            channels.insert(0, pick(rng, MIDDLE))
        keep_touches = True
        if buys and rng.random() < 0.05:   # a buyer we never tracked
            keep_touches = False
        if buys and conv <= LAST and conv >= datetime.datetime(2026, 9, 1):
            conversions.append({"user_id": user, "conversion_time": stamp(conv),
                                "revenue": "%.2f" % rng.choice(PRICES)})
            if rng.random() < 0.15:   # a touch after the purchase (a receipt email, a retargeting ad)
                after = conv + datetime.timedelta(minutes=rng.randint(10, 5 * 24 * 60))
                if after <= LAST:
                    times.append(after)
                    channels.append(rng.choice(("email", "paid_social")))
        if keep_touches:
            for t, ch in zip(times, channels):
                if FIRST <= t <= LAST:
                    touches.append({"user_id": user, "touch_time": stamp(t), "channel": ch})
    touches.sort(key=lambda r: (r["touch_time"], r["user_id"], r["channel"]))
    conversions.sort(key=lambda r: (r["conversion_time"], r["user_id"]))
    return {"touchpoints": touches, "conversions": conversions}


def write_csv(rows, path, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_all(tables, folder):
    for name in ("touchpoints", "conversions"):
        write_csv(tables[name], os.path.join(folder, name + ".csv"), FIELDS[name])


def main():
    tables = build()
    write_all(tables, os.path.join(HERE, "data"))
    print("wrote", len(tables["touchpoints"]), "touchpoints and", len(tables["conversions"]), "conversions")


if __name__ == "__main__":
    main()
