"""Exercise: bucket UTC timestamps into days, ISO weeks and months in a chosen time zone.

ZONES, the export window, load_csv, parse_utc, nth_sunday, day_key, month_key,
week_monday and main are done for you. Fill in the functions marked TODO.
Then run: python3 test_lesson.py
"""
import csv
import os
from datetime import date, datetime, time, timedelta, timezone

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Fixed offsets. India has no daylight saving time, so IST is always UTC+5:30.
# PST is UTC-8 by definition; Pacific clocks show it only from early November to
# early March. "PT" (Pacific time) follows the US daylight saving rule: see to_pacific.
ZONES = {
    "UTC": timezone.utc,
    "IST": timezone(timedelta(hours=5, minutes=30), "IST"),
    "PST": timezone(timedelta(hours=-8), "PST"),
}
PDT = timezone(timedelta(hours=-7), "PDT")

# The export window, from the export job's log: start included, end excluded.
DATA_START = datetime(2025, 12, 8, tzinfo=timezone.utc)
DATA_END = datetime(2026, 1, 19, tzinfo=timezone.utc)


def load_csv(name, data_dir=DATA):
    with open(os.path.join(data_dir, name), newline="") as f:
        return list(csv.DictReader(f))


def parse_utc(text):
    """'2025-12-31T20:00:00Z' -> a timezone-aware datetime in UTC."""
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def nth_sunday(year, month, n):
    """The date of the n-th Sunday of a month."""
    first = date(year, month, 1)
    first_sunday = first + timedelta(days=(6 - first.weekday()) % 7)
    return first_sunday + timedelta(days=7 * (n - 1))


def to_pacific(dt):
    """US Pacific time with daylight saving, built from the rule (in force since 2007).

    Clocks go forward at 02:00 PST on the second Sunday of March (10:00 UTC) and
    back at 02:00 PDT on the first Sunday of November (09:00 UTC).
    """
    # TODO: convert dt to UTC, build the two switch instants for that year with
    # nth_sunday and datetime.combine(..., time(hour), tzinfo=timezone.utc), then
    # return the instant on PDT if it falls between them, else on ZONES["PST"].
    raise NotImplementedError


def to_zone(dt, zone):
    """The same instant, shown on the clock of `zone` ('UTC', 'IST', 'PST' or 'PT')."""
    # TODO: 'PT' goes through to_pacific; the others use ZONES.
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


def complete_weeks(weekly, data_start, data_end, zone):
    """Keep only the weeks that the data covers from Monday 00:00 to the next Monday 00:00 on the `zone` clock.

    data_start (included) and data_end (excluded) are aware datetimes: the export window.
    """
    # TODO: show data_start and data_end on the zone clock and drop the tzinfo, so you
    # compare wall-clock times. A week is complete when its Monday 00:00 is not before
    # the local start and the next Monday 00:00 is not after the local end.
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
    weekly = count_by(stamps, iso_week_key, "IST")
    full = complete_weeks(weekly, DATA_START, DATA_END, "IST")
    print("IST weeks left out as partial:", [wk for wk in weekly if wk not in full])
    for row in week_over_week(full):
        print(row)


if __name__ == "__main__":
    main()
