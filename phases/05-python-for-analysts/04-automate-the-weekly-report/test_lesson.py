"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py."""
import importlib.util
import os
import tempfile
import unittest
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)

DATA = os.path.join(HERE, "data", "orders.csv")
WEEK = date(2026, 10, 19)


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
        rev = "| Revenue | $%s | $%s | %+.1f%% |" % (format(cur["revenue"], ",.2f"), format(prev["revenue"], ",.2f"),
                                                    (cur["revenue"] - prev["revenue"]) / prev["revenue"] * 100)
        self.assertIn(rev, lines)
        orders = "| Paid orders | %d | %d | %+.1f%% |" % (cur["orders"], prev["orders"], (cur["orders"] - prev["orders"]) / prev["orders"] * 100)
        self.assertIn(orders, lines)
        aov = "| Average order value | $%s | $%s | %+.1f%% |" % (format(cur["aov"], ",.2f"), format(prev["aov"], ",.2f"),
                                                            (cur["aov"] - prev["aov"]) / prev["aov"] * 100)
        self.assertIn(aov, lines)
        rate = "| Refund rate | %.1f%% | %.1f%% | %+.1f pts |" % (cur["refund_rate"], prev["refund_rate"], cur["refund_rate"] - prev["refund_rate"])
        self.assertIn(rate, lines)

    def test_default_week_and_bad_week(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = lesson.main(["--out", tmp, "--data", DATA])
            self.assertTrue(path.endswith("report-2026-10-19.md"))
            with self.assertRaises(SystemExit):
                lesson.main(["--week", "2026-10-20", "--out", tmp, "--data", DATA])


if __name__ == "__main__":
    unittest.main()
