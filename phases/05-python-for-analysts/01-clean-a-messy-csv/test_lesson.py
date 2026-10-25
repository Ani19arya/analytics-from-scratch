"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py."""
import csv
import importlib.util
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)


def raw_rows():
    with open(os.path.join(HERE, "data", "orders_raw.csv"), newline="") as f:
        return list(csv.DictReader(f))


class TestCleanCsv(unittest.TestCase):
    def test_parse_date_formats(self):
        for s in ["2026-09-14", "14/09/2026", "Sep 14, 2026", "14-Sep-2026"]:
            self.assertEqual(lesson.parse_date(s), "2026-09-14", s)
        self.assertEqual(lesson.parse_date("03/04/2026"), "2026-04-03")
        self.assertIsNone(lesson.parse_date("TBD"))
        self.assertIsNone(lesson.parse_date(""))

    def test_parse_amount(self):
        self.assertEqual(lesson.parse_amount("$1,200.50"), (1200.5, "USD"))
        self.assertEqual(lesson.parse_amount("USD 75"), (75.0, "USD"))
        self.assertEqual(lesson.parse_amount(" INR 45,000 "), (45000.0, "INR"))
        self.assertEqual(lesson.parse_amount("INR 1,20,000"), (120000.0, "INR"))
        self.assertEqual(lesson.parse_amount("Rs 999"), (999.0, "INR"))
        self.assertIsNone(lesson.parse_amount("about 50"))
        self.assertIsNone(lesson.parse_amount("12 apples"))

    def test_report_counts(self):
        raw = raw_rows()
        clean, report = lesson.clean_rows(raw)
        self.assertEqual(report["rows_in"], 106)
        self.assertEqual(report["rows_out"], 91)
        self.assertEqual(len(clean), 91)
        self.assertEqual(report["dropped"], {"blank_date": 3, "bad_date": 2, "blank_amount": 4, "duplicate": 6})
        self.assertEqual(len(report["dropped_rows"]), 15)
        self.assertEqual(report["filled_city"], 3)
        expected_trim = sum(1 for r in raw for v in r.values() if v != " ".join(v.split()))
        self.assertEqual(report["trimmed_cells"], expected_trim)

    def test_clean_rows_are_clean(self):
        clean, _ = lesson.clean_rows(raw_rows())
        ids = [r["order_id"] for r in clean]
        self.assertEqual(len(ids), len(set(ids)), "a duplicate order survived")
        for r in clean:
            self.assertRegex(r["order_date"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertIsInstance(r["amount"], float)
            self.assertIn(r["currency"], ("USD", "INR"))
            self.assertEqual(r["customer"], " ".join(r["customer"].split()))
            self.assertNotEqual(r["city"], "")
        first = clean[0]
        self.assertEqual(first, {"order_id": "1001", "order_date": "2026-09-21", "customer": "Farah Khan",
                                 "city": "Austin", "amount": 130700.0, "currency": "INR"})


if __name__ == "__main__":
    unittest.main()
