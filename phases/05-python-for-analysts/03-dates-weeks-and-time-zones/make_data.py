"""Build data/signups.csv: synthetic sign-up events with UTC timestamps.

The events run from Monday 8 December 2025 00:00 UTC up to (not including)
Monday 19 January 2026 00:00 UTC, so they cross a year end and six ISO weeks.

    python3 make_data.py     # writes data/signups.csv for the default seed
    build(seed)              # returns {"signups": rows}, values as strings like the CSV
"""
import csv
import os
import random
from datetime import datetime, timedelta

DEFAULT_SEED = 503

START = datetime(2025, 12, 8)
SECONDS = 42 * 24 * 3600  # six weeks
END = START + timedelta(seconds=SECONDS)


def build(seed=DEFAULT_SEED, n=700):
    rng = random.Random(seed)
    stamps = sorted(START + timedelta(seconds=rng.randrange(SECONDS)) for _ in range(n))
    return {"signups": [{"event_id": str(i), "ts_utc": ts.strftime("%Y-%m-%dT%H:%M:%SZ")}
                        for i, ts in enumerate(stamps, 1)]}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    rows = build()["signups"]
    with open(os.path.join(data, "signups.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["event_id", "ts_utc"])
        w.writeheader()
        w.writerows(rows)
    print("wrote", len(rows), "events")


if __name__ == "__main__":
    main()
