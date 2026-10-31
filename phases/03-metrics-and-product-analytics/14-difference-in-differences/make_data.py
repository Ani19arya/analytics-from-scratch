"""Build a synthetic panel for a food delivery app that launched a weekly lunch
plan in one city (Pune) from week 9, and not in three other cities.

zone_weeks.csv: city, zone, week, week_start, orders
  one row per delivery zone per week, weeks 1 to 16, 6 zones per city.

The data is synthetic and deterministic (fixed seed). Every city shares the same
seasonal pattern (a slow monsoon rise and a festival bump in weeks 12 and 13).
Pune gets a true lift of LIFT orders per zone-week from the launch week. Nagpur
also grows by NAGPUR_TREND orders per zone each week for its own reasons (a rival
app is closing down there), so it does not move in parallel with Pune.

    python3 make_data.py          writes data/zone_weeks.csv (seed 7)
    import make_data; make_data.build(seed=5)   returns the rows for another seed
"""
import csv
import datetime
import os
import random

SEED = 7
HERE = os.path.dirname(os.path.abspath(__file__))
FIELDS = ["city", "zone", "week", "week_start", "orders"]
CITIES = {"Pune": 160, "Nashik": 105, "Indore": 130, "Nagpur": 120}   # typical orders per zone-week
TREATED = "Pune"
LAUNCH_WEEK = 9
WEEKS = 16
ZONES = 6
LIFT = 14.0
NAGPUR_TREND = 3.0
FIRST_MONDAY = datetime.date(2026, 6, 1)


def season(week):
    """Shared by every city: a slow rise, and a festival bump in weeks 12 and 13."""
    return 2.5 * (week - 1) + (15.0 if week in (12, 13) else 0.0)


def build(seed=SEED):
    """Return the zone-week rows as dictionaries of text values."""
    rng = random.Random(seed)
    rows = []
    for city in sorted(CITIES):
        for z in range(1, ZONES + 1):
            zone = "%s-%d" % (city[:3].upper(), z)
            base = CITIES[city] + rng.uniform(-20, 20)
            for week in range(1, WEEKS + 1):
                y = base + season(week) + rng.gauss(0, 4)
                if city == "Nagpur":
                    y += NAGPUR_TREND * (week - 1)
                if city == TREATED and week >= LAUNCH_WEEK:
                    y += LIFT
                start = FIRST_MONDAY + datetime.timedelta(weeks=week - 1)
                rows.append({"city": city, "zone": zone, "week": str(week),
                             "week_start": start.isoformat(), "orders": str(max(0, int(round(y))))})
    return rows


def write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    rows = build()
    write_csv(rows, os.path.join(HERE, "data", "zone_weeks.csv"))
    print("wrote %d zone-weeks" % len(rows))


if __name__ == "__main__":
    main()
