"""Tests for lesson 02. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Expected answers come from Python's statistics module and plain formulas here,
never from the solution file. The intervals are checked on the committed data
AND on a second dataset built in memory with another seed."""
import ast
import csv
import importlib.util
import math
import os
import statistics
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ORDERS = os.path.join(HERE, "data", "orders.csv")
SURVEY = os.path.join(HERE, "data", "survey.csv")
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")
BANNED = {"statistics", "numpy", "pandas", "scipy", "statsmodels"}
OTHER_SEED = 31
# t for 95% and df 17, from a printed t table, typed independently of the lesson's table.
T95_DF17 = 2.110


def load():
    spec = importlib.util.spec_from_file_location("lesson_module", TARGET)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def imported_modules(path):
    with open(path) as f:
        tree = ast.parse(f.read())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def column(path, name):
    with open(path, newline="") as f:
        return [float(r[name]) for r in csv.DictReader(f)]


m = load()


class TestRules(unittest.TestCase):
    def test_no_statistics_module(self):
        used = imported_modules(TARGET) & BANNED
        self.assertFalse(used, "Write the formulas yourself: remove the import of %s." % ", ".join(sorted(used)))


class TestPieces(unittest.TestCase):
    def test_sample_sd(self):
        vals = [2, 4, 4, 4, 5, 5, 7, 9]
        self.assertAlmostEqual(m.sample_sd(vals), statistics.stdev(vals), places=9,
                               msg="divide the squared deviations by n - 1, not n")

    def test_sample_sd_needs_two(self):
        for vals in ([5], []):
            with self.assertRaises(ValueError):
                m.sample_sd(vals)

    def test_sample_sd_of_a_tie_is_zero(self):
        self.assertEqual(m.sample_sd([5, 5]), 0)

    def test_critical_values(self):
        self.assertAlmostEqual(m.critical_value(4), 2.776)
        self.assertAlmostEqual(m.critical_value(9, 0.99), 3.250)
        self.assertAlmostEqual(m.critical_value(30), 2.042, msg="df 30 is still in the t table")
        self.assertAlmostEqual(m.critical_value(31), 1.96, msg="above df 30 the lesson switches to z")
        self.assertAlmostEqual(m.critical_value(100), 1.96)
        self.assertAlmostEqual(m.critical_value(31, 0.90), 1.6449)


class TestIntervals(unittest.TestCase):
    def test_mean_ci_small_sample_uses_t(self):
        low, high = m.mean_ci(list(range(1, 11)))
        self.assertAlmostEqual(low, 3.3343, places=3, msg="n = 10, so use t with df 9 (2.262)")
        self.assertAlmostEqual(high, 7.6657, places=3)

    def test_mean_ci_large_sample_uses_z(self):
        vals = [i % 7 for i in range(100)]
        mean = statistics.mean(vals)
        margin = 1.96 * statistics.stdev(vals) / math.sqrt(100)
        low, high = m.mean_ci(vals)
        self.assertAlmostEqual(low, mean - margin, places=9)
        self.assertAlmostEqual(high, mean + margin, places=9)

    def test_mean_ci_edge_cases(self):
        self.assertEqual(tuple(m.mean_ci([5, 5])), (5, 5), "no spread means zero width")
        with self.assertRaises(ValueError):
            m.mean_ci([5])

    def test_proportion_ci(self):
        low, high = m.proportion_ci(120, 400)
        self.assertAlmostEqual(low, 0.2551, places=4)
        self.assertAlmostEqual(high, 0.3449, places=4)

    def test_proportion_ci_edge_cases(self):
        self.assertEqual(tuple(m.proportion_ci(0, 50)), (0, 0),
                         "Wald with zero successes has zero width (a known weakness, see Common mistakes)")
        with self.assertRaises(ValueError, msg="n = 0 has no rate"):
            m.proportion_ci(0, 0)
        with self.assertRaises(ValueError, msg="more successes than people is impossible"):
            m.proportion_ci(11, 10)

    def test_higher_confidence_is_wider(self):
        a = m.proportion_ci(120, 400, 0.90)
        b = m.proportion_ci(120, 400, 0.99)
        self.assertLess(a[1] - a[0], b[1] - b[0])


class TestOnData(unittest.TestCase):
    def check_orders(self, path):
        vals = column(path, "order_value")
        self.assertEqual(len(vals), 18)
        margin = T95_DF17 * statistics.stdev(vals) / math.sqrt(len(vals))
        low, high = m.mean_ci(m.read_column(path, "order_value"))
        self.assertAlmostEqual(low, statistics.mean(vals) - margin, places=6)
        self.assertAlmostEqual(high, statistics.mean(vals) + margin, places=6)

    def check_survey(self, path):
        answers = column(path, "would_reorder")
        k, n = int(sum(answers)), len(answers)
        p = k / n
        for conf, z in ((0.95, 1.96), (0.99, 2.5758)):
            margin = z * math.sqrt(p * (1 - p) / n)
            low, high = m.proportion_ci(int(sum(m.read_column(path, "would_reorder"))), n, conf)
            self.assertAlmostEqual(low, p - margin, places=9)
            self.assertAlmostEqual(high, p + margin, places=9)

    def test_read_column(self):
        self.assertEqual(m.read_column(ORDERS, "order_value"), column(ORDERS, "order_value"))

    def test_committed_data(self):
        self.check_orders(ORDERS)
        self.check_survey(SURVEY)

    def test_second_dataset(self):
        sys.path.insert(0, HERE)
        import make_data
        sys.path.pop(0)
        with tempfile.TemporaryDirectory() as folder:
            make_data.write_all(folder, make_data.build(seed=OTHER_SEED))
            orders = os.path.join(folder, "orders.csv")
            self.assertNotEqual(column(orders, "order_value"), column(ORDERS, "order_value"))
            self.check_orders(orders)
            self.check_survey(os.path.join(folder, "survey.csv"))


if __name__ == "__main__":
    unittest.main()
