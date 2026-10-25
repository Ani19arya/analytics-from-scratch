"""Tests for lesson 02. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead."""
import csv
import importlib.util
import math
import os
import statistics
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ORDERS = os.path.join(HERE, "data", "orders.csv")
SURVEY = os.path.join(HERE, "data", "survey.csv")
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


def column(path, name):
    with open(path, newline="") as f:
        return [float(r[name]) for r in csv.DictReader(f)]


class TestPieces(unittest.TestCase):
    def test_sample_sd(self):
        vals = [2, 4, 4, 4, 5, 5, 7, 9]
        self.assertAlmostEqual(m.sample_sd(vals), statistics.stdev(vals), places=9)

    def test_sample_sd_needs_two(self):
        with self.assertRaises(ValueError):
            m.sample_sd([5])

    def test_critical_values(self):
        self.assertAlmostEqual(m.critical_value(4), 2.776)
        self.assertAlmostEqual(m.critical_value(9, 0.99), 3.250)
        self.assertAlmostEqual(m.critical_value(100), 1.96)
        self.assertAlmostEqual(m.critical_value(31, 0.90), 1.6449)


class TestIntervals(unittest.TestCase):
    def test_mean_ci_small_sample_uses_t(self):
        low, high = m.mean_ci(list(range(1, 11)))
        self.assertAlmostEqual(low, 3.3343, places=3)
        self.assertAlmostEqual(high, 7.6657, places=3)

    def test_mean_ci_large_sample_uses_z(self):
        vals = [i % 7 for i in range(100)]
        mean = statistics.mean(vals)
        margin = 1.96 * statistics.stdev(vals) / math.sqrt(100)
        low, high = m.mean_ci(vals)
        self.assertAlmostEqual(low, mean - margin, places=9)
        self.assertAlmostEqual(high, mean + margin, places=9)

    def test_proportion_ci(self):
        low, high = m.proportion_ci(120, 400)
        self.assertAlmostEqual(low, 0.2551, places=4)
        self.assertAlmostEqual(high, 0.3449, places=4)

    def test_higher_confidence_is_wider(self):
        a = m.proportion_ci(120, 400, 0.90)
        b = m.proportion_ci(120, 400, 0.99)
        self.assertLess(a[1] - a[0], b[1] - b[0])


class TestOnData(unittest.TestCase):
    def test_read_column(self):
        self.assertEqual(m.read_column(ORDERS, "order_value"), column(ORDERS, "order_value"))

    def test_orders_interval(self):
        vals = column(ORDERS, "order_value")
        n = len(vals)
        margin = 2.110 * statistics.stdev(vals) / math.sqrt(n)  # df = 17
        low, high = m.mean_ci(m.read_column(ORDERS, "order_value"))
        self.assertAlmostEqual(low, statistics.mean(vals) - margin, places=6)
        self.assertAlmostEqual(high, statistics.mean(vals) + margin, places=6)

    def test_survey_interval_contains_sample_rate(self):
        answers = m.read_column(SURVEY, "would_reorder")
        k = int(sum(answers))
        low, high = m.proportion_ci(k, len(answers))
        self.assertLess(low, k / len(answers))
        self.assertGreater(high, k / len(answers))


if __name__ == "__main__":
    unittest.main()
