"""Exercise: bucket UTC timestamps into days, ISO weeks and months in a chosen time zone.

ZONES, load_csv, parse_utc, day_key, month_key, week_monday and main are done for you.
Fill in the functions marked TODO. Then run: python3 test_lesson.py
"""
import csv
import os
from datetime import date, datetime, timedelta, timezone

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Fixed offsets. PST is UTC-8 only outside US daylight saving time, which is true for
# every date in this lesson. For real reports across the year use zoneinfo instead.
ZONES = {
    "UTC": timezone.utc,
    "IST": timezone(timedelta(hours=5, minutes=30)),
    "PST": timezone(timedelta(hours=-8)),
}


def load_csv(name, data_dir=DATA):
    with open(os.path.join(data_dir, name), newline="") as f:
        return list(csv.DictReader(f))


def parse_utc(text):
    """'2025-12-31T20:00:00Z' -> a timezone-aware datetime in UTC."""
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def to_zone(dt, zone):
    """The same instant, shown on the clock of `zone` ('UTC', 'IST' or 'PST')."""
    # TODO
    raise NotImplementedError

def day_key(dt):
    return dt.strftime("%Y-%m-%d")


def month_key(dt):
    return dt.strftime("%Y-%m")


def iso_week_key(dt):
    """ISO year and week, e.g. '2026-W01'. Uses the ISO year, not the calendar year."""
    # TODO: use dt.isocalendar(), and pad the week to two digits.
    raise NotImplementedError

def count_by(timestamps, key_fn, zone):
    """Convert each UTC datetime to `zone`, bucket it with key_fn, return {key: count} sorted by key."""
    # TODO
    raise NotImplementedError

def week_monday(week_key):
    year, week = week_key.split("-W")
    return date.fromisocalendar(int(year), int(week), 1)


def previous_week(week_key):
    """The week 7 days earlier, found by date arithmetic, so 2026-W01 -> 2025-W52."""
    # TODO: do not subtract 1 from the week number.
    raise NotImplementedError

def week_over_week(weekly):
    """weekly: {week_key: count}. Returns one dict per week from the first to the last key.

    Weeks with no events count as 0. change_pct is rounded to 1 decimal and is None
    when there is no previous week or the previous count is 0.
    """
    # TODO
    raise NotImplementedError

def main():
    stamps = [parse_utc(r["ts_utc"]) for r in load_csv("signups.csv")]
    for zone in ("UTC", "IST", "PST"):
        days = count_by(stamps, day_key, zone)
        print(zone, "31 Dec:", days.get("2025-12-31", 0), " 1 Jan:", days.get("2026-01-01", 0),
              " months:", count_by(stamps, month_key, zone))
    print()
    for row in week_over_week(count_by(stamps, iso_week_key, "IST")):
        print(row)


if __name__ == "__main__":
    main()
