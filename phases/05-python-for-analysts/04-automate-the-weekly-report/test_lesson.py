"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py."""
import csv
import importlib.util
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_data  # noqa: E402

TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)

DATA = os.path.join(HERE, "data", "orders.csv")
WEEK = date(2026, 10, 19)
OTHER_SEED = 2027


def last_full_monday(rows):
    """Walk back from the last date to a Sunday, then back 6 more days."""
    d = max(r["order_date"] for r in rows)
    while d.weekday() != 6:
        d -= timedelta(days=1)
    return d - timedelta(days=6)


def report_lines(cur, prev):
    """The four table rows, built here from plain numbers."""
    def pct(c, p):
        return "%+.1f%%" % ((c - p) / p * 100)
    return [
        "| Revenue | $%s | $%s | %s |" % (format(cur["revenue"], ",.2f"), format(prev["revenue"], ",.2f"), pct(cur["revenue"], prev["revenue"])),
        "| Paid orders | %d | %d | %s |" % (cur["orders"], prev["orders"], pct(cur["orders"], prev["orders"])),
        "| Average order value | $%s | $%s | %s |" % (format(cur["aov"], ",.2f"), format(prev["aov"], ",.2f"), pct(cur["aov"], prev["aov"])),
        "| Refund rate | %.1f%% | %.1f%% | %+.1f pts |" % (cur["refund_rate"], prev["refund_rate"], cur["refund_rate"] - prev["refund_rate"]),
    ]


def manual_kpis(rows, monday):
    week = [r for r in rows if monday <= r["order_date"] <= monday + timedelta(days=6)]
    paid = [r["amount"] for r in week if r["status"] == "paid"]
    refunded = len(week) - len(paid)
    return {"revenue": round(sum(paid), 2), "orders": len(paid),
            "aov": round(sum(paid), 2) / len(paid), "refund_rate": refunded / len(week) * 100}


class TestWeeklyReport(unittest.TestCase):
    def setUp(self):
        self.rows = lesson.load_orders(DATA)

    def test_latest_complete_week(self):
        self.assertEqual(lesson.latest_complete_week(self.rows), WEEK)
        short = [r for r in self.rows if r["order_date"] <= date(2026, 10, 22)]
        self.assertEqual(lesson.latest_complete_week(short), date(2026, 10, 12))

    def test_rows_in_week(self):
        week = lesson.rows_in_week(self.rows, WEEK)
        self.assertTrue(week)
        self.assertTrue(all(WEEK <= r["order_date"] <= date(2026, 10, 25) for r in week))
        total = sum(len(lesson.rows_in_week(self.rows, WEEK - timedelta(days=7 * k))) for k in range(3))
        self.assertEqual(total, len(self.rows))

    def test_kpis(self):
        for monday in (WEEK, WEEK - timedelta(days=7)):
            got = lesson.compute_kpis(lesson.rows_in_week(self.rows, monday))
            want = manual_kpis(self.rows, monday)
            self.assertEqual(got["orders"], want["orders"])
            for k in ("revenue", "aov", "refund_rate"):
                self.assertAlmostEqual(got[k], want[k], places=6, msg=k)
        empty = lesson.compute_kpis([])
        self.assertEqual(empty["orders"], 0)
        self.assertIsNone(empty["aov"])
        self.assertIsNone(empty["refund_rate"])

    def test_changes(self):
        self.assertAlmostEqual(lesson.pct_change(110, 100), 10.0)
        self.assertIsNone(lesson.pct_change(5, 0))
        self.assertIsNone(lesson.pct_change(None, 5))
        self.assertEqual(lesson.format_change("revenue", 90, 100), "-10.0%")
        self.assertEqual(lesson.format_change("orders", 3, 0), "n/a")
        self.assertEqual(lesson.format_change("refund_rate", 5.0, 4.2), "+0.8 pts")

    def test_report_file(self):
        cur, prev = manual_kpis(self.rows, WEEK), manual_kpis(self.rows, WEEK - timedelta(days=7))
        with tempfile.TemporaryDirectory() as tmp:
            path = lesson.main(["--week", "2026-10-19", "--out", tmp, "--data", DATA])
            self.assertEqual(os.path.basename(path), "report-2026-10-19.md")
            with open(path) as f:
                lines = f.read().splitlines()
        self.assertEqual(lines[0], "# Weekly report: week of 2026-10-19")
        self.assertIn("| KPI | This week | Last week | Change |", lines)
        for want in report_lines(cur, prev):
            self.assertIn(want, lines, "this table row is missing or formatted differently: " + want)
        self.assertTrue(any("Refunds can arrive" in line for line in lines),
                        "the report must warn that the latest week's refund rate can still rise (refund lag)")

    def test_default_week_and_bad_week(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = lesson.main(["--out", tmp, "--data", DATA])
            self.assertTrue(path.endswith("report-2026-10-19.md"))
            with self.assertRaises(SystemExit):
                lesson.main(["--week", "2026-10-20", "--out", tmp, "--data", DATA])


    def test_second_dataset(self):
        """Another seed, ending on a Friday, built in memory. Hard-coded numbers fail here."""
        rows = make_data.build(OTHER_SEED, days=19)["orders"]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "orders.csv")
            with open(path, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=make_data.FIELDS)
                w.writeheader()
                w.writerows(rows)
            loaded = lesson.load_orders(path)
            monday = last_full_monday(loaded)
            self.assertEqual(monday, date(2026, 10, 12), "the data ends on Friday 23 October, so the last full week starts 12 October")
            self.assertEqual(lesson.latest_complete_week(loaded), monday)
            out = lesson.main(["--out", tmp, "--data", path])
            self.assertEqual(os.path.basename(out), "report-2026-10-12.md")
            with open(out) as f:
                lines = f.read().splitlines()
        cur, prev = manual_kpis(loaded, monday), manual_kpis(loaded, monday - timedelta(days=7))
        for want in report_lines(cur, prev):
            self.assertIn(want, lines, "seed %d: this row is wrong or missing: %s" % (OTHER_SEED, want))


class TestSmallCases(unittest.TestCase):
    def test_tie_and_zero(self):
        self.assertEqual(lesson.format_change("revenue", 100.0, 100.0), "+0.0%", "no change is +0.0%, not n/a")
        self.assertEqual(lesson.format_change("refund_rate", 4.0, 4.0), "+0.0 pts")
        self.assertEqual(lesson.format_change("revenue", 0.0, 0.0), "n/a", "a change from 0 is undefined")
        self.assertEqual(lesson.format_change("refund_rate", None, 4.0), "n/a")

    def test_report_with_an_empty_previous_week(self):
        cur = lesson.compute_kpis([{"order_date": WEEK, "amount": 50.0, "status": "paid"},
                                   {"order_date": WEEK, "amount": 30.0, "status": "refunded"}])
        self.assertEqual(cur, {"revenue": 50.0, "orders": 1, "aov": 50.0, "refund_rate": 50.0})
        lines = lesson.build_report(WEEK, cur, lesson.compute_kpis([])).splitlines()
        self.assertIn("| Revenue | $50.00 | $0.00 | n/a |", lines)
        self.assertIn("| Average order value | $50.00 | n/a | n/a |", lines, "no paid orders last week, so its AOV is n/a")
        self.assertIn("| Refund rate | 50.0% | n/a | n/a |", lines)


if __name__ == "__main__":
    unittest.main()
