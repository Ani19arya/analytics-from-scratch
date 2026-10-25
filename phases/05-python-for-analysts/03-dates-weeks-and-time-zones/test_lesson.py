"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py."""
import csv
import importlib.util
import os
import unittest
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)


def stamps():
    with open(os.path.join(HERE, "data", "signups.csv"), newline="") as f:
        return [lesson.parse_utc(r["ts_utc"]) for r in csv.DictReader(f)]


class TestDates(unittest.TestCase):
    def test_iso_week_at_year_end(self):
        self.assertEqual(lesson.iso_week_key(datetime(2025, 12, 28)), "2025-W52")
        self.assertEqual(lesson.iso_week_key(datetime(2025, 12, 31)), "2026-W01")
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
        self.assertEqual(lesson.previous_week("2021-W01"), "2020-W53")

    def test_count_by_day_matches_manual_offset(self):
        ts = stamps()
        got = lesson.count_by(ts, lesson.day_key, "IST")
        manual = {}
        for t in ts:
            k = (t.replace(tzinfo=None) + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d")
            manual[k] = manual.get(k, 0) + 1
        self.assertEqual(got, dict(sorted(manual.items())))
        self.assertEqual(list(got), sorted(got))
        self.assertNotEqual(got, lesson.count_by(ts, lesson.day_key, "UTC"))

    def test_week_over_week_fills_gaps_and_crosses_year(self):
        rows = lesson.week_over_week({"2025-W52": 10, "2026-W02": 5})
        self.assertEqual([r["week"] for r in rows], ["2025-W52", "2026-W01", "2026-W02"])
        self.assertEqual(rows[0]["prev_count"], None)
        self.assertEqual(rows[0]["change_pct"], None)
        self.assertEqual(rows[1], {"week": "2026-W01", "count": 0, "prev_week": "2025-W52", "prev_count": 10, "change_pct": -100.0})
        self.assertEqual(rows[2]["change_pct"], None, "previous count is 0, so the change is undefined")

    def test_weekly_on_data(self):
        ts = stamps()
        weekly = lesson.count_by(ts, lesson.iso_week_key, "UTC")
        self.assertEqual(list(weekly), ["2025-W50", "2025-W51", "2025-W52", "2026-W01", "2026-W02", "2026-W03"])
        self.assertEqual(sum(weekly.values()), 700)
        rows = lesson.week_over_week(weekly)
        w01 = [r for r in rows if r["week"] == "2026-W01"][0]
        self.assertEqual(w01["prev_count"], weekly["2025-W52"])
        self.assertEqual(w01["change_pct"], round((weekly["2026-W01"] - weekly["2025-W52"]) / weekly["2025-W52"] * 100, 1))


if __name__ == "__main__":
    unittest.main()
