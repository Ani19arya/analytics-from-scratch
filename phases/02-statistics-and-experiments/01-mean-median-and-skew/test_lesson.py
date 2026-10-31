"""Tests for lesson 01. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Expected answers come from Python's statistics module and plain loops here,
never from the solution file. The pipeline is checked on the committed data
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
DATA = os.path.join(HERE, "data", "postings.csv")
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")
BANNED = {"statistics", "numpy", "pandas", "scipy", "statsmodels"}
OTHER_SEED = 7


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


def build_other_dataset(folder):
    sys.path.insert(0, HERE)
    import make_data
    sys.path.pop(0)
    rows = make_data.build(seed=OTHER_SEED)["postings"]
    path = os.path.join(folder, "postings.csv")
    make_data.write_csv(path, rows)
    return path, [float(r["pay_mid"]) for r in rows]


def ref_percentile(values, p):
    """Linear interpolation, written independently: same rule as Excel PERCENTILE.INC."""
    s = sorted(values)
    pos = (len(s) - 1) * p / 100
    i = int(pos)
    if i + 1 < len(s):
        return s[i] + (s[i + 1] - s[i]) * (pos - i)
    return float(s[i])


m = load()


class TestRules(unittest.TestCase):
    def test_no_statistics_module(self):
        used = imported_modules(TARGET) & BANNED
        self.assertFalse(used, "Write the arithmetic yourself: remove the import of %s." % ", ".join(sorted(used)))


class TestMeanMedian(unittest.TestCase):
    def test_mean_small(self):
        self.assertAlmostEqual(m.mean([1, 2, 3, 4]), 2.5)

    def test_mean_with_zeros(self):
        self.assertAlmostEqual(m.mean([0, 0, 0, 10]), 2.5, msg="zeros count as values in the mean")

    def test_median_odd(self):
        self.assertEqual(m.median([7, 1, 3]), 3, "sort first, then take the middle value")

    def test_median_even(self):
        self.assertAlmostEqual(m.median([10, 1, 4, 3]), 3.5, msg="even count: average the two middle values")

    def test_median_tie_and_single(self):
        self.assertEqual(m.median([2, 3, 1, 2]), 2)
        self.assertEqual(m.median([5]), 5)

    def test_empty_raises(self):
        for fn in (m.mean, m.median, m.std_dev):
            with self.assertRaises(ValueError, msg="%s([]) should raise ValueError" % fn.__name__):
                fn([])
        with self.assertRaises(ValueError):
            m.percentile([], 50)

    def test_outlier_moves_mean_not_median(self):
        base = [50, 60, 70, 80, 90]
        with_outlier = [50, 60, 70, 80, 900]
        self.assertAlmostEqual(m.median(base), m.median(with_outlier))
        self.assertGreater(m.mean(with_outlier), m.mean(base) * 2)

    def test_skew_labels(self):
        self.assertEqual(m.skew_label([1, 2, 3, 4, 5]), "symmetric")
        self.assertEqual(m.skew_label([1, 2, 3, 4, 50]), "right")
        self.assertEqual(m.skew_label([-50, 2, 3, 4, 5]), "left")
        self.assertEqual(m.skew_label([0, 0, 0]), "symmetric", "all zeros: no gap, so symmetric")


class TestSpread(unittest.TestCase):
    def test_std_dev(self):
        vals = [2, 4, 4, 4, 5, 5, 7, 9]
        self.assertAlmostEqual(m.std_dev(vals), statistics.pstdev(vals), places=9,
                               msg="divide by n here, the whole list is the data")
        self.assertEqual(m.std_dev([3, 3, 3]), 0, "identical values have no spread")

    def test_percentile_small(self):
        vals = [10, 20, 30, 40]
        self.assertAlmostEqual(m.percentile(vals, 0), 10)
        self.assertAlmostEqual(m.percentile(vals, 100), 40)
        self.assertAlmostEqual(m.percentile(vals, 50), 25)
        self.assertAlmostEqual(m.percentile(vals, 25), 17.5, msg="rank 0.75: three quarters of the way from 10 to 20")
        self.assertAlmostEqual(m.percentile([4, 1, 3], 50), 3, msg="sort before you pick a position")

    def test_percentile_bad_p(self):
        with self.assertRaises(ValueError):
            m.percentile([1, 2], 101)

    def test_percentile_matches_statistics_quartiles(self):
        vals = [3, 7, 8, 5, 12, 14, 21, 13, 18]
        q1, q2, q3 = statistics.quantiles(vals, n=4, method="inclusive")
        self.assertAlmostEqual(m.percentile(vals, 25), q1)
        self.assertAlmostEqual(m.percentile(vals, 50), q2)
        self.assertAlmostEqual(m.percentile(vals, 75), q3)

    def test_histogram_keeps_empty_bins(self):
        got = m.histogram([1, 3, 12, 31], 10)
        self.assertEqual(list(got), [(0, 2), (10, 1), (20, 0), (30, 1)],
                         "every bin from the lowest to the highest, with 0 for empty ones")
        self.assertEqual(list(m.histogram([], 10)), [])

    def test_histogram_edge_belongs_to_upper_bin(self):
        self.assertEqual(list(m.histogram([10, 19.99, 20], 10)), [(10, 2), (20, 1)])


class TestOnPostings(unittest.TestCase):
    def check_summary(self, path, pay):
        s = m.summarise(path)
        self.assertEqual(s["n"], len(pay))
        self.assertAlmostEqual(s["mean"], statistics.mean(pay), places=6)
        self.assertAlmostEqual(s["median"], statistics.median(pay), places=6)
        self.assertAlmostEqual(s["gap"], statistics.mean(pay) - statistics.median(pay), places=6,
                               msg="gap is mean minus median")
        self.assertAlmostEqual(s["sd"], statistics.pstdev(pay), places=4)
        self.assertAlmostEqual(s["p25"], ref_percentile(pay, 25), places=6)
        self.assertAlmostEqual(s["p75"], ref_percentile(pay, 75), places=6)
        self.assertEqual(s["skew"], "right")

    def test_read_pay(self):
        with open(DATA, newline="") as f:
            pay = [float(r["pay_mid"]) for r in csv.DictReader(f)]
        self.assertEqual(m.read_pay(DATA), pay)

    def test_summary_on_committed_data(self):
        with open(DATA, newline="") as f:
            pay = [float(r["pay_mid"]) for r in csv.DictReader(f)]
        self.check_summary(DATA, pay)

    def test_summary_on_second_dataset(self):
        with tempfile.TemporaryDirectory() as folder:
            path, pay = build_other_dataset(folder)
            self.assertNotEqual(statistics.median(pay), 83000.0, "the second dataset should differ")
            self.check_summary(path, pay)

    def test_histogram_on_data(self):
        pay = m.read_pay(DATA)
        bins = list(m.histogram(pay, 10000))
        self.assertEqual(sum(c for _, c in bins), len(pay), "every posting lands in exactly one bin")
        self.assertEqual(bins[0][0], math.floor(min(pay) / 10000) * 10000)
        self.assertEqual(bins[-1][0], math.floor(max(pay) / 10000) * 10000)
        for (a, _), (b, _) in zip(bins, bins[1:]):
            self.assertEqual(b - a, 10000, "no bin may be skipped, even an empty one")


if __name__ == "__main__":
    unittest.main()
