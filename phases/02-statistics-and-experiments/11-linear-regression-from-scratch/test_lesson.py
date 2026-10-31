"""Tests for lesson 11. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Expected answers are computed here by different routes, never read from the
solution file:
- slope and intercept from the one-pass sums formula;
- R squared as r squared (true for a line with one x);
- the slope's standard error as (sy / sx) * sqrt((1 - r^2) / (n - 2)), which
  is algebraically the same as sqrt(SSE / (n - 2)) / sqrt(Sxx);
- on Python 3.10 and later, slope and intercept are also checked against
  statistics.linear_regression (skipped on 3.9).
Everything runs on the committed data AND on a second dataset built in memory
from make_data.build(seed=OTHER_SEED)."""
import ast
import csv
import importlib.util
import math
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "members.csv")
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")
BANNED = {"statistics", "numpy", "pandas", "scipy", "statsmodels", "sklearn"}
OTHER_SEED = 2024
HAS_LINREG = sys.version_info >= (3, 10)


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


def pairs_of(path):
    xs, ys = [], []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r["spend_30d"] != "":
                xs.append(int(r["visits_30d"]))
                ys.append(float(r["spend_30d"]))
    return xs, ys


def ref(xs, ys):
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxy = sum(x * y for x, y in zip(xs, ys))
    sxx = sum(x * x for x in xs)
    syy = sum(y * y for y in ys)
    slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    intercept = (sy - slope * sx) / n
    r = (n * sxy - sx * sy) / math.sqrt((n * sxx - sx * sx) * (n * syy - sy * sy))
    sd_x = math.sqrt((sxx - sx * sx / n) / (n - 1))
    sd_y = math.sqrt((syy - sy * sy / n) / (n - 1))
    se = (sd_y / sd_x) * math.sqrt((1 - r * r) / (n - 2))
    return slope, intercept, r * r, se


m = load()


class TestRules(unittest.TestCase):
    def test_no_statistics_library(self):
        used = imported_modules(TARGET) & BANNED
        self.assertFalse(used, "Fit the line yourself: remove the import of %s." % ", ".join(sorted(used)))


class TestFit(unittest.TestCase):
    def test_hand_example(self):
        xs, ys = [1, 2, 3, 4, 5], [3, 5, 4, 7, 8]
        fit = m.fit_line(xs, ys)
        self.assertAlmostEqual(fit["slope"], 1.2, places=12, msg="slope = Sxy / Sxx = 12 / 10 for this toy example")
        self.assertAlmostEqual(fit["intercept"], 1.8, places=12, msg="intercept = mean(y) - slope * mean(x) = 5.4 - 1.2 * 3")
        self.assertAlmostEqual(m.predict(fit, 10), 13.8, places=12)
        self.assertAlmostEqual(m.r_squared(xs, ys, fit), ref(xs, ys)[2], places=12)
        self.assertAlmostEqual(m.slope_se(xs, ys, fit), ref(xs, ys)[3], places=12,
                               msg="slope SE = sqrt(SSE / (n - 2)) / sqrt(Sxx); divide by n - 2, not n")

    def test_perfect_line(self):
        xs = [0, 1, 2, 3]
        ys = [2 + 3 * x for x in xs]
        fit = m.fit_line(xs, ys)
        self.assertAlmostEqual(fit["slope"], 3.0, places=12)
        self.assertAlmostEqual(fit["intercept"], 2.0, places=12)
        self.assertAlmostEqual(m.r_squared(xs, ys, fit), 1.0, places=12)
        self.assertAlmostEqual(m.slope_se(xs, ys, fit), 0.0, places=12)

    def test_flat_y(self):
        fit = m.fit_line([1, 2, 3], [4, 4, 4])
        self.assertAlmostEqual(fit["slope"], 0.0, places=12)
        self.assertAlmostEqual(fit["intercept"], 4.0, places=12)
        with self.assertRaises(ValueError, msg="y does not vary: R squared is 0 / 0, raise ValueError"):
            m.r_squared([1, 2, 3], [4, 4, 4], fit)

    def test_errors(self):
        for xs, ys in (([], []), ([1], [2]), ([1, 2], [1]), ([5, 5, 5], [1, 2, 3])):
            with self.assertRaises(ValueError, msg="fit_line(%r, %r) should raise ValueError" % (xs, ys)):
                m.fit_line(xs, ys)
        fit = m.fit_line([1, 2], [3, 5])
        with self.assertRaises(ValueError, msg="2 points: the line goes through both, no residual variance is left"):
            m.slope_se([1, 2], [3, 5], fit)

    def test_ci(self):
        low, high = m.slope_ci(2.0, 0.5)
        self.assertAlmostEqual(low, 1.02, places=12)
        self.assertAlmostEqual(high, 2.98, places=12)
        low, high = m.slope_ci(2.0, 0.5, crit=2.0)
        self.assertAlmostEqual(low, 1.0, places=12)

    def test_r_squared_is_not_about_slope(self):
        xs = list(range(10))
        noise = [3, -3, 2, -2, 1, -1, 2, -2, 3, -3]
        steep = [10 * x + e for x, e in zip(xs, noise)]
        flat = [0.5 * x + e for x, e in zip(xs, noise)]
        r2_steep = m.r_squared(xs, steep, m.fit_line(xs, steep))
        r2_flat = m.r_squared(xs, flat, m.fit_line(xs, flat))
        self.assertGreater(r2_steep, 0.95)
        self.assertLess(r2_flat, 0.3, "the same noise around a flatter line leaves a much lower R squared")


class TestOnData(unittest.TestCase):
    def check(self, path):
        xs, ys = pairs_of(path)
        got_x, got_y = m.read_members(path)
        self.assertEqual((list(got_x), list(got_y)), (xs, ys),
                         "visits and spend in file order, members with a blank spend skipped (not read as 0)")
        slope, intercept, r2, se = ref(xs, ys)
        s = m.summarise(path)
        self.assertEqual(s["n"], len(xs))
        self.assertAlmostEqual(s["slope"], round(slope, 4), places=4)
        self.assertAlmostEqual(s["intercept"], round(intercept, 4), places=4)
        self.assertAlmostEqual(s["r_squared"], round(r2, 4), places=4, msg="with one x, R squared equals r squared")
        self.assertAlmostEqual(s["slope_se"], round(se, 4), places=4)
        self.assertAlmostEqual(s["slope_ci"][0], round(slope - 1.96 * se, 4), places=3)
        self.assertAlmostEqual(s["slope_ci"][1], round(slope + 1.96 * se, 4), places=3)
        self.assertAlmostEqual(s["residual_sd"], round(se * math.sqrt(sum((x - sum(xs) / len(xs)) ** 2 for x in xs)), 4),
                               places=3, msg="residual_sd is sqrt(SSE / (n - 2))")
        return slope

    def test_committed_data(self):
        self.check(DATA)

    def test_second_dataset(self):
        sys.path.insert(0, HERE)
        import make_data
        sys.path.pop(0)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "members.csv")
            make_data.write_csv(path, make_data.build(seed=OTHER_SEED)["members"])
            slope = self.check(path)
            self.assertNotAlmostEqual(slope, ref(*pairs_of(DATA))[0], places=4, msg="the second dataset should differ")

    @unittest.skipUnless(HAS_LINREG, "statistics.linear_regression needs Python 3.10 or later")
    def test_matches_statistics_module(self):
        import statistics
        xs, ys = pairs_of(DATA)
        want = statistics.linear_regression(xs, ys)
        fit = m.fit_line(xs, ys)
        self.assertAlmostEqual(fit["slope"], want.slope, places=9, msg="your slope should match statistics.linear_regression")
        self.assertAlmostEqual(fit["intercept"], want.intercept, places=9)


if __name__ == "__main__":
    unittest.main()
