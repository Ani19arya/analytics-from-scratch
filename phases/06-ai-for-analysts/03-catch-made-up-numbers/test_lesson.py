"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py."""
import csv
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)


def read(name):
    with open(os.path.join(HERE, "data", name), newline="") as f:
        return list(csv.DictReader(f))


class TestMadeUpNumbers(unittest.TestCase):
    def test_extract_simple(self):
        got = lesson.extract_numbers("Revenue was $156,142 from 240 orders, up 30.6% on 1.50 per unit.")
        self.assertEqual(got, [(156142.0, 0), (240.0, 0), (30.6, 1), (1.5, 2)])

    def test_extract_sentence_end_and_none(self):
        self.assertEqual(lesson.extract_numbers("West made $52,000."), [(52000.0, 0)])
        self.assertEqual(lesson.extract_numbers("No numbers here."), [])

    def test_mismatched_counts_raise(self):
        rows = read("orders.csv")
        bad = [{"sentence_id": "X", "metrics": "total_revenue;order_count", "sentence": "Revenue was 5."}]
        with self.assertRaises(ValueError):
            lesson.check_summary(rows, bad)

    def test_flags_exactly_the_fabricated_numbers(self):
        rows = read("orders.csv")
        results = lesson.check_summary(rows, read("ai_summary.csv"))
        self.assertEqual(len(results), 11)
        flagged = sorted((r["sentence_id"], r["metric"]) for r in results if not r["ok"])
        self.assertEqual(flagged, [("S3", "north_share_pct"), ("S4", "west_revenue"), ("S5", "growth_pct")])

    def test_actuals_are_independent_of_the_text(self):
        rows = read("orders.csv")
        results = lesson.check_summary(rows, read("ai_summary.csv"))
        by = {r["metric"]: r for r in results}
        self.assertEqual(by["total_revenue"]["actual"], sum(int(r["revenue"]) for r in rows))
        self.assertEqual(by["west_revenue"]["actual"], sum(int(r["revenue"]) for r in rows if r["region"] == "West"))
        self.assertEqual(by["west_revenue"]["claimed"], 52000.0)


if __name__ == "__main__":
    unittest.main()
