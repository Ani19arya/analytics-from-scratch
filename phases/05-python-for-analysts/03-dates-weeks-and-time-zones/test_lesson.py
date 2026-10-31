"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py.

Expected answers are computed here in plain Python with fixed offsets, never read
from the solution. The daylight saving check against the time zone database runs
only when that database is installed (it often is not on Windows).
"""
import csv
import importlib.util
import os
import sys
import unittest
from datetime import date, datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_data  # noqa: E402

TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)

try:
    from zoneinfo import ZoneInfo
    LA = ZoneInfo("America/Los_Angeles")
    HAVE_TZDATA = True
except Exception:  # Python 3.8, or no time zone database installed
    HAVE_TZDATA = False

OTHER_SEED = 2027
OFFSET = {"UTC": timedelta(0), "IST": timedelta(hours=5, minutes=30), "PST": timedelta(hours=-8)}
WINDOW = (datetime(2025, 12, 8, tzinfo=timezone.utc), datetime(2026, 1, 19, tzinfo=timezone.utc))


def stamps_from(rows):
    return [lesson.parse_utc(r["ts_utc"]) for r in rows]


def stamps():
    with open(os.path.join(HERE, "data", "signups.csv"), newline="") as f:
        return stamps_from(csv.DictReader(f))


def manual_count(ts, zone, fmt):
    """Shift the naive UTC clock by the zone's fixed offset, then format. No tzinfo involved."""
    out = {}
    for t in ts:
        k = (t.replace(tzinfo=None) + OFFSET[zone]).strftime(fmt)
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


def manual_weeks(ts, zone):
    out = {}
    for t in ts:
        y, w, _ = (t.replace(tzinfo=None) + OFFSET[zone]).isocalendar()
        k = "%d-W%02d" % (y, w)
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


def manual_complete(weekly, zone, start, end):
    """A week is complete when its local Monday 00:00 and the next one, moved back to UTC, sit inside the window."""
    keep = {}
    for wk, n in weekly.items():
        y, w = wk.split("-W")
        monday_utc = datetime.combine(date.fromisocalendar(int(y), int(w), 1), datetime.min.time()) - OFFSET[zone]
        if start.replace(tzinfo=None) <= monday_utc and monday_utc + timedelta(days=7) <= end.replace(tzinfo=None):
            keep[wk] = n
    return keep


class TestDates(unittest.TestCase):
    def test_iso_week_at_year_end(self):
        self.assertEqual(lesson.iso_week_key(datetime(2025, 12, 28)), "2025-W52")
        self.assertEqual(lesson.iso_week_key(datetime(2025, 12, 31)), "2026-W01",
                         "31 Dec 2025 is in ISO week 1 of 2026: take the year from isocalendar() too")
        self.assertEqual(lesson.iso_week_key(datetime(2026, 1, 4)), "2026-W01")
        self.assertEqual(lesson.iso_week_key(datetime(2026, 1, 5)), "2026-W02")

    def test_time_zone_moves_the_day(self):
        ts = lesson.parse_utc("2025-12-31T20:00:00Z")
        self.assertEqual(lesson.day_key(lesson.to_zone(ts, "UTC")), "2025-12-31")
        self.assertEqual(lesson.day_key(lesson.to_zone(ts, "IST")), "2026-01-01")
        self.assertEqual(lesson.month_key(lesson.to_zone(ts, "IST")), "2026-01")
        early = lesson.parse_utc("2026-01-01T05:00:00Z")
        self.assertEqual(lesson.day_key(lesson.to_zone(early, "PST")), "2025-12-31")

    def test_previous_week(self):
        self.assertEqual(lesson.previous_week("2026-W02"), "2026-W01")
        self.assertEqual(lesson.previous_week("2026-W01"), "2025-W52")
        self.assertEqual(lesson.previous_week("2021-W01"), "2020-W53", "2020 has 53 ISO weeks")

    def test_week_over_week_fills_gaps_and_crosses_year(self):
        rows = lesson.week_over_week({"2025-W52": 10, "2026-W02": 5})
        self.assertEqual([r["week"] for r in rows], ["2025-W52", "2026-W01", "2026-W02"])
        self.assertEqual(rows[0]["prev_count"], None)
        self.assertEqual(rows[0]["change_pct"], None)
        self.assertEqual(rows[1], {"week": "2026-W01", "count": 0, "prev_week": "2025-W52", "prev_count": 10, "change_pct": -100.0})
        self.assertEqual(rows[2]["change_pct"], None, "previous count is 0, so the change is undefined")

    def test_empty_inputs(self):
        self.assertEqual(lesson.week_over_week({}), [])
        self.assertEqual(lesson.count_by([], lesson.day_key, "IST"), {})
        self.assertEqual(lesson.complete_weeks({}, WINDOW[0], WINDOW[1], "IST"), {})

    def test_tie_and_same_count(self):
        rows = lesson.week_over_week({"2026-W01": 7, "2026-W02": 7})
        self.assertEqual(rows[1]["change_pct"], 0.0, "equal counts are a 0.0% change, not None")


class TestDaylightSaving(unittest.TestCase):
    """The guaranteed path: the US rule built by hand, checked on instants worked out on paper."""

    def check(self, utc_text, want_local, want_offset_hours):
        got = lesson.to_zone(lesson.parse_utc(utc_text), "PT")
        self.assertEqual(got.strftime("%Y-%m-%d %H:%M:%S"), want_local, "%s on the Pacific clock" % utc_text)
        self.assertEqual(got.utcoffset(), timedelta(hours=want_offset_hours), "%s: wrong offset" % utc_text)

    def test_spring_forward(self):
        self.check("2026-03-08T09:59:59Z", "2026-03-08 01:59:59", -8)
        self.check("2026-03-08T10:00:00Z", "2026-03-08 03:00:00", -7)

    def test_fall_back(self):
        self.check("2026-11-01T08:59:59Z", "2026-11-01 01:59:59", -7)
        self.check("2026-11-01T09:00:00Z", "2026-11-01 01:00:00", -8)

    def test_winter_matches_pst(self):
        ts = stamps()
        self.assertEqual(lesson.count_by(ts, lesson.day_key, "PT"), lesson.count_by(ts, lesson.day_key, "PST"),
                         "every date in this data is in winter, so PT and PST must agree")

    def test_summer_fixed_offset_picks_the_wrong_day(self):
        ts = lesson.parse_utc("2026-07-01T07:30:00Z")
        self.assertEqual(lesson.day_key(lesson.to_zone(ts, "PT")), "2026-07-01")
        self.assertEqual(lesson.day_key(lesson.to_zone(ts, "PST")), "2026-06-30")

    @unittest.skipUnless(HAVE_TZDATA, "no time zone database (zoneinfo/tzdata); the hand-built rule is still tested above")
    def test_against_the_time_zone_database(self):
        t, end = datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2027, 1, 1, tzinfo=timezone.utc)
        while t < end:
            mine, ref = lesson.to_zone(t, "PT"), t.astimezone(LA)
            self.assertEqual((mine.replace(tzinfo=None), mine.utcoffset()), (ref.replace(tzinfo=None), ref.utcoffset()),
                             "Pacific time differs from the tz database at %s UTC" % t)
            t += timedelta(hours=1)
        day = datetime(2026, 3, 9, tzinfo=LA).astimezone(timezone.utc) - datetime(2026, 3, 8, tzinfo=LA).astimezone(timezone.utc)
        self.assertEqual(day, timedelta(hours=23), "8 March 2026 has 23 hours in Los Angeles")


class TestOnData(unittest.TestCase):
    def check_dataset(self, ts, label):
        for zone in ("UTC", "IST", "PST"):
            self.assertEqual(lesson.count_by(ts, lesson.day_key, zone), manual_count(ts, zone, "%Y-%m-%d"),
                             "%s: daily counts on the %s clock are wrong; convert first, then bucket" % (label, zone))
            weekly = lesson.count_by(ts, lesson.iso_week_key, zone)
            self.assertEqual(weekly, manual_weeks(ts, zone), "%s: weekly counts in %s are wrong" % (label, zone))
            self.assertEqual(lesson.complete_weeks(weekly, WINDOW[0], WINDOW[1], zone),
                             manual_complete(weekly, zone, *WINDOW),
                             "%s: complete_weeks in %s kept a partial week or dropped a full one" % (label, zone))

    def test_committed_file(self):
        ts = stamps()
        self.assertEqual(len(ts), 700)
        self.check_dataset(ts, "committed file")
        got = lesson.count_by(ts, lesson.day_key, "IST")
        self.assertEqual(list(got), sorted(got), "count_by must return keys sorted")
        self.assertNotEqual(got, lesson.count_by(ts, lesson.day_key, "UTC"))

    def test_second_dataset(self):
        """Another seed, built in memory. A table of hard-coded counts fails here."""
        self.check_dataset(stamps_from(make_data.build(OTHER_SEED)["signups"]), "seed %d" % OTHER_SEED)

    def test_partial_weeks_are_dropped(self):
        ts = stamps()
        ist = lesson.complete_weeks(lesson.count_by(ts, lesson.iso_week_key, "IST"), WINDOW[0], WINDOW[1], "IST")
        self.assertNotIn("2026-W04", ist, "2026-W04 has only a few hours of data on the IST clock")
        self.assertNotIn("2025-W50", ist, "the data starts at 05:30 on Monday on the IST clock, so W50 is partial too")
        self.assertEqual(list(ist), ["2025-W51", "2025-W52", "2026-W01", "2026-W02", "2026-W03"])
        utc = lesson.complete_weeks(lesson.count_by(ts, lesson.iso_week_key, "UTC"), WINDOW[0], WINDOW[1], "UTC")
        self.assertEqual(len(utc), 6, "on the UTC clock the window is exactly six full weeks")

    def test_weekly_on_data(self):
        weekly = lesson.count_by(stamps(), lesson.iso_week_key, "UTC")
        self.assertEqual(list(weekly), ["2025-W50", "2025-W51", "2025-W52", "2026-W01", "2026-W02", "2026-W03"])
        self.assertEqual(sum(weekly.values()), 700)
        rows = lesson.week_over_week(weekly)
        w01 = [r for r in rows if r["week"] == "2026-W01"][0]
        self.assertEqual(w01["prev_count"], weekly["2025-W52"])
        self.assertEqual(w01["change_pct"], round((weekly["2026-W01"] - weekly["2025-W52"]) / weekly["2025-W52"] * 100, 1))


if __name__ == "__main__":
    unittest.main()
