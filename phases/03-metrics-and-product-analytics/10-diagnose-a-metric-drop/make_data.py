"""Build data/daily_users.csv for a synthetic food delivery app, 8 to 22 October 2026.

One row per day, platform, app version and city:
    date, platform, app_version, city, server_users, dau

server_users counts distinct users the backend saw that day (any logged-in API call).
dau counts distinct users whose app sent an "app_open" analytics event. Normally dau
is about 96 to 97% of server_users, because some analytics events are always lost.

The data is synthetic and deterministic (fixed seed). App version 7.4 for both mobile
platforms rolls out on 21 October and becomes a forced update on 22 October. On one
mobile platform (picked by the seed) version 7.4 has an analytics bug: most app_open
events are never sent, so dau collapses while server_users stays normal. For the
default seed that is android, and total DAU falls about 20% on 22 October.

    python3 make_data.py          writes data/daily_users.csv (seed 53)
    import make_data; make_data.build(seed=6)   returns the rows for another seed
"""
import csv
import datetime
import os
import random

SEED = 53
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "daily_users.csv")
START = datetime.date(2026, 10, 8)
END = datetime.date(2026, 10, 22)
FIELDS = ["date", "platform", "app_version", "city", "server_users", "dau"]
CITIES = {"Pune": 520, "Mumbai": 760, "Nagpur": 230, "Nashik": 190}   # weekday users
PLATFORMS = {"android": 0.50, "ios": 0.30, "web": 0.20}
NEW_VERSION_SHARE = {datetime.date(2026, 10, 21): 0.10, datetime.date(2026, 10, 22): 0.45}
WEEKDAY_FACTOR = {4: 1.08, 5: 1.18, 6: 1.14}   # Friday, Saturday, Sunday
COVERAGE = 0.965      # share of server users whose app_open event arrives
BUG_COVERAGE = 0.08   # the same share on the broken version


def build(seed=SEED):
    """Return {"daily_users": [row, ...]}, each row a dict of text values."""
    rng = random.Random(seed)
    buggy = rng.choice(("android", "ios"))
    rows = []
    day = START
    while day <= END:
        factor = WEEKDAY_FACTOR.get(day.weekday(), 1.0)
        new_share = NEW_VERSION_SHARE.get(day, 0.0)
        for city, base in CITIES.items():
            for platform, share in PLATFORMS.items():
                users = int(round(base * share * factor * rng.gauss(1.0, 0.04)))
                if platform == "web":
                    versions = [("web", users)]
                else:
                    new = int(round(users * new_share))
                    versions = [("7.3", users - new), ("7.4", new)]
                for version, n in versions:
                    if n <= 0:
                        continue
                    cov = BUG_COVERAGE if (platform == buggy and version == "7.4") else COVERAGE
                    dau = sum(1 for _ in range(n) if rng.random() < cov)
                    rows.append({"date": day.isoformat(), "platform": platform, "app_version": version,
                                 "city": city, "server_users": str(n), "dau": str(dau)})
        day += datetime.timedelta(days=1)
    return {"daily_users": rows}


def write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    rows = build()["daily_users"]
    write_csv(rows, OUT)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
