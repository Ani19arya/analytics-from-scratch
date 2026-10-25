"""Tests for lesson 01. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead."""
import csv
import importlib.util
import os
import statistics
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "postings.csv")
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")


def load():
    spec = importlib.util.spec_from_file_location("lesson_module", TARGET)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load()


class TestMeanMedian(unittest.TestCase):
    def test_mean_small(self):
        self.assertAlmostEqual(m.mean([1, 2, 3, 4]), 2.5)

    def test_median_odd(self):
        self.assertEqual(m.median([7, 1, 3]), 3)

    def test_median_even(self):
        self.assertAlmostEqual(m.median([10, 1, 4, 3]), 3.5)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            m.mean([])
        with self.assertRaises(ValueError):
            m.median([])

    def test_outlier_moves_mean_not_median(self):
        base = [50, 60, 70, 80, 90]
        with_outlier = [50, 60, 70, 80, 900]
        self.assertAlmostEqual(m.median(base), m.median(with_outlier))
        self.assertGreater(m.mean(with_outlier), m.mean(base) * 2)

    def test_skew_labels(self):
        self.assertEqual(m.skew_label([1, 2, 3, 4, 5]), "symmetric")
        self.assertEqual(m.skew_label([1, 2, 3, 4, 50]), "right")
        self.assertEqual(m.skew_label([-50, 2, 3, 4, 5]), "left")


class TestOnPostings(unittest.TestCase):
    def setUp(self):
        with open(DATA, newline="") as f:
            self.pay = [float(r["pay_mid"]) for r in csv.DictReader(f)]

    def test_read_pay(self):
        self.assertEqual(m.read_pay(DATA), self.pay)

    def test_summary_matches_reference(self):
        s = m.summarise(DATA)
        self.assertEqual(s["n"], len(self.pay))
        self.assertAlmostEqual(s["mean"], statistics.mean(self.pay), places=6)
        self.assertAlmostEqual(s["median"], statistics.median(self.pay), places=6)
        self.assertAlmostEqual(s["gap"], s["mean"] - s["median"], places=6)

    def test_pay_is_right_skewed(self):
        self.assertEqual(m.summarise(DATA)["skew"], "right")


if __name__ == "__main__":
    unittest.main()
