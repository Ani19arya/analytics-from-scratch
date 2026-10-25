"""Build data/signups.csv: synthetic sign-up events with UTC timestamps.

The events run from Monday 8 December 2025 to Sunday 18 January 2026, so they
cross a year end and six ISO weeks. Run: python3 make_data.py
"""
import csv
import os
import random
from datetime import datetime, timedelta

random.seed(503)

START = datetime(2025, 12, 8)
SECONDS = 42 * 24 * 3600  # six weeks


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    stamps = sorted(START + timedelta(seconds=random.randrange(SECONDS)) for _ in range(700))
    with open(os.path.join(data, "signups.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["event_id", "ts_utc"])
        for i, ts in enumerate(stamps, 1):
            w.writerow([i, ts.strftime("%Y-%m-%dT%H:%M:%SZ")])
    print("wrote", len(stamps), "events")


if __name__ == "__main__":
    main()
