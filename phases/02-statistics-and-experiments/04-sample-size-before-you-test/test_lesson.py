"""Tests for lesson 04. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Expected answers come from the formula written out here with published z values,
never from the solution file. The plan is checked on the committed data AND on
a second dataset built in memory with another seed."""
import ast
import csv
import importlib.util
import math
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "pages.csv")
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")
BANNED = {"statistics", "numpy", "pandas", "scipy", "statsmodels"}
OTHER_SEED = 5

Z975 = 1.959963984540054
Z80 = 0.8416212335729143


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


m = load()


def reference_n(p1, p2, za=Z975, zb=Z80):
    p_bar = (p1 + p2) / 2
    top = (za * math.sqrt(2 * p_bar * (1 - p_bar))
           + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    return top / (p2 - p1) ** 2


class TestRules(unittest.TestCase):
    def test_no_statistics_library(self):
        used = imported_modules(TARGET) & BANNED
        self.assertFalse(used, "Write the bisection yourself: remove the import of %s." % ", ".join(sorted(used)))


class TestQuantile(unittest.TestCase):
    def test_known_quantiles(self):
        self.assertAlmostEqual(m.z_quantile(0.975), Z975, places=6)
        self.assertAlmostEqual(m.z_quantile(0.80), Z80, places=6)
        self.assertAlmostEqual(m.z_quantile(0.5), 0.0, places=6)

    def test_round_trip(self):
        for p in (0.01, 0.2, 0.9, 0.995):
            self.assertAlmostEqual(m.normal_cdf(m.z_quantile(p)), p, places=9,
                                   msg="halve the interval at least 100 times")


class TestSampleSize(unittest.TestCase):
    def test_ten_to_twelve_percent(self):
        n = m.sample_size_per_group(0.10, 0.12)
        self.assertIsInstance(n, int, "users come in whole numbers: round up with math.ceil")
        self.assertEqual(n, math.ceil(reference_n(0.10, 0.12)))
        self.assertEqual(n, 3841)

    def test_rounds_up(self):
        n = m.sample_size_per_group(0.20, 0.25)
        self.assertGreaterEqual(n, reference_n(0.20, 0.25))
        self.assertLess(n - reference_n(0.20, 0.25), 1)

    def test_equal_rates_raise(self):
        with self.assertRaises(ValueError):
            m.sample_size_per_group(0.1, 0.1)
        with self.assertRaises(ValueError):
            m.sample_size_for_lift(0.1, 0)

    def test_drop_needs_the_same_users_as_a_rise(self):
        self.assertEqual(m.sample_size_per_group(0.12, 0.10), m.sample_size_per_group(0.10, 0.12),
                         "a two-sided test is symmetric in p1 and p2")

    def test_relative_not_absolute(self):
        n = m.sample_size_for_lift(0.056, 0.10)
        self.assertEqual(n, math.ceil(reference_n(0.056, 0.056 * 1.10)),
                         "a 10% lift on 5.6% is 6.16%, not 15.6%")

    def test_halving_the_lift_roughly_quadruples_n(self):
        big = m.sample_size_for_lift(0.10, 0.20)
        small = m.sample_size_for_lift(0.10, 0.10)
        self.assertEqual(big, math.ceil(reference_n(0.10, 0.12)))
        ratio = small / big
        self.assertGreater(ratio, 3.5)
        self.assertLess(ratio, 4.5)

    def test_more_power_needs_more_users(self):
        self.assertGreater(m.sample_size_per_group(0.10, 0.12, power=0.90),
                           m.sample_size_per_group(0.10, 0.12, power=0.80))

    def test_weeks(self):
        self.assertEqual(m.weeks_needed(3841, 5000), 2, "both groups need users: 3,841 x 2 / 5,000")
        self.assertEqual(m.weeks_needed(2500, 5000), 1)
        self.assertEqual(m.weeks_needed(100, 5000, min_weeks=2), 2, "never fewer than min_weeks")
        self.assertEqual(m.weeks_needed(0, 5000), 1)
        with self.assertRaises(ValueError):
            m.weeks_needed(100, 0)


class TestPlan(unittest.TestCase):
    def check_plan(self, path, lift, min_weeks):
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))
        got = m.plan(path, lift, min_weeks=min_weeks)
        self.assertEqual([r["page"] for r in got], [r["page"] for r in rows], "keep the file order")
        for g, r in zip(got, rows):
            base = float(r["baseline_rate"])
            weekly = int(r["weekly_visitors"])
            n = math.ceil(reference_n(base, base * (1 + lift)))
            self.assertLessEqual(abs(g["n_per_group"] - n), 1, "page %s" % r["page"])
            self.assertEqual(g["weekly_visitors"], weekly)
            self.assertEqual(g["weeks"], max(math.ceil(g["n_per_group"] * 2 / weekly), min_weeks),
                             "page %s: weeks = ceil(n x 2 / weekly visitors), at least min_weeks" % r["page"])
        return got

    def test_plan_on_committed_data(self):
        for lift in (0.20, 0.10, 0.05):
            self.check_plan(DATA, lift, 2)
        self.check_plan(DATA, 0.10, 1)

    def test_plan_default_runs_two_full_weeks(self):
        for row in m.plan(DATA, 0.20):
            self.assertGreaterEqual(row["weeks"], 2, "the default plan covers two full weekly cycles")

    def test_plan_on_second_dataset(self):
        sys.path.insert(0, HERE)
        import make_data
        sys.path.pop(0)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "pages.csv")
            make_data.write_csv(path, make_data.build(seed=OTHER_SEED)["pages"])
            with open(path, newline="") as f, open(DATA, newline="") as g:
                self.assertNotEqual(f.read(), g.read(), "the second dataset should differ")
            for lift in (0.20, 0.10):
                self.check_plan(path, lift, 2)


if __name__ == "__main__":
    unittest.main()
