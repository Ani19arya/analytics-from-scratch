"""Tests for lesson 06. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Expected answers come from Python's statistics module (quantiles with
method="inclusive", median, mean, stdev) and plain loops here, never from the
solution file. The pipeline is checked on the committed data AND on a second
dataset built in memory with another seed."""
import ast
import csv
import importlib.util
import os
import statistics
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "salaries.csv")
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")
BANNED = {"statistics", "numpy", "pandas", "scipy", "statsmodels"}
OTHER_SEED = 13


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


def read(path):
    with open(path, newline="") as f:
        return [(int(r["response_id"]), float(r["base_pay"])) for r in csv.DictReader(f)]


def ref_quartiles(values):
    if len(values) == 1:
        return values[0], values[0], values[0]
    return tuple(statistics.quantiles(values, n=4, method="inclusive"))


def ref_describe(values):
    q1, med, q3 = ref_quartiles(values)
    return {"n": len(values), "mean": statistics.mean(values), "sd": statistics.stdev(values),
            "median": statistics.median(values), "iqr": q3 - q1,
            "mad": statistics.median([abs(v - statistics.median(values)) for v in values])}


def ref_fences(values):
    q1, _, q3 = ref_quartiles(values)
    return q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)


m = load()


class TestRules(unittest.TestCase):
    def test_no_statistics_module(self):
        used = imported_modules(TARGET) & BANNED
        self.assertFalse(used, "Write the arithmetic yourself: remove the import of %s." % ", ".join(sorted(used)))


class TestQuartiles(unittest.TestCase):
    pay = [61000, 64000, 70000, 72000, 75000, 81000, 88000, 205000]

    def test_inclusive_method(self):
        got = tuple(m.quartiles(self.pay))
        want = ref_quartiles(self.pay)
        self.assertEqual(want, (68500.0, 73500.0, 82750.0))
        for g, w in zip(got, want):
            self.assertAlmostEqual(g, w, msg="use rank = p / 100 * (n - 1); (65500, 73500, 86250) "
                                             "would be the exclusive method, Excel QUARTILE.EXC")

    def test_sorts_first(self):
        self.assertEqual(tuple(m.quartiles([4, 1, 3, 2])), (1.75, 2.5, 3.25), "sort the values before picking ranks")

    def test_single_value_and_empty(self):
        self.assertEqual(tuple(m.quartiles([5])), (5, 5, 5), "one value is every quartile")
        with self.assertRaises(ValueError):
            m.quartiles([])
        with self.assertRaises(ValueError):
            m.percentile([1, 2], 101)

    def test_percentile_ends(self):
        self.assertAlmostEqual(m.percentile([3, 9, 1], 0), 1)
        self.assertAlmostEqual(m.percentile([3, 9, 1], 100), 9)


class TestOutliers(unittest.TestCase):
    pay = [61000, 64000, 70000, 72000, 75000, 81000, 88000, 205000]

    def test_fences(self):
        low, high = m.iqr_fences(self.pay)
        self.assertAlmostEqual(low, 47125.0, msg="low fence = Q1 - 1.5 * IQR = 68500 - 1.5 * 14250")
        self.assertAlmostEqual(high, 104125.0)
        low3, high3 = m.iqr_fences(self.pay, k=3)
        self.assertAlmostEqual(high3, 82750 + 3 * 14250, msg="k sets how many IQRs the fence sits from the box")

    def test_flag(self):
        self.assertEqual(list(m.flag_outliers(self.pay)), [205000])
        self.assertEqual(list(m.flag_outliers([5])), [], "one value cannot be an outlier")

    def test_value_on_a_fence_is_not_flagged(self):
        # Q1 = 2, Q3 = 4, IQR = 2, high fence = 7
        self.assertEqual(list(m.flag_outliers([1, 2, 3, 4, 7])), [], "7 sits exactly on the fence, so it stays")

    def test_tie_makes_iqr_zero(self):
        self.assertEqual(list(m.flag_outliers([5, 5, 5, 5, 9])), [9],
                         "with IQR 0 the fences close on the box, so any other value is flagged")

    def test_box_plot_stats(self):
        box = m.box_plot_stats(self.pay)
        self.assertAlmostEqual(box["iqr"], 14250.0)
        self.assertEqual(box["low_whisker"], 61000, "the low whisker is the smallest value inside the fences")
        self.assertEqual(box["high_whisker"], 88000, "the high whisker stops at the last value inside the fence")
        self.assertEqual(list(box["outliers"]), [205000])


class TestRobust(unittest.TestCase):
    def test_mad(self):
        pay = [61000, 64000, 70000, 72000, 75000, 81000, 88000, 205000]
        self.assertAlmostEqual(m.mad(pay), 8500.0, msg="distances from the median 73,500, then their median")
        self.assertEqual(m.mad([0, 0, 0, 10]), 0, "more than half the values sit on the median, so the MAD is 0")
        self.assertEqual(m.mad([7]), 0)

    def test_robust_versus_classic(self):
        pay = [61000, 64000, 70000, 72000, 75000, 81000, 88000, 205000]
        wild = pay + [2050000]
        self.assertGreater(m.sample_sd(wild), 10 * m.sample_sd(pay), "one wild value inflates the SD")
        self.assertLess(m.mad(wild) - m.mad(pay), 5000, "the MAD barely moves")
        self.assertAlmostEqual(m.sample_sd(pay), statistics.stdev(pay), places=6, msg="divide by n - 1")
        with self.assertRaises(ValueError):
            m.sample_sd([1])
        with self.assertRaises(ValueError):
            m.mean([])


class OnData:
    def test_summary(self):
        rows = read(self.path)
        pay = [v for _, v in rows]
        s = m.summarise(self.path)
        errors = sorted(i for i, v in rows if v < 1000)
        self.assertEqual(list(s["errors"]), errors, "entry errors are the rows with pay under 1,000")
        low, high = ref_fences(pay)
        outliers = sorted(v for v in pay if v < low or v > high)
        self.assertEqual(s["flagged"], len(outliers))
        box = s["box"]
        q1, med, q3 = ref_quartiles(pay)
        for key, want in (("q1", q1), ("median", med), ("q3", q3), ("iqr", q3 - q1),
                          ("low_fence", low), ("high_fence", high)):
            self.assertAlmostEqual(box[key], want, places=6, msg="box[%r] should be %s" % (key, want))
        inside = [v for v in pay if low <= v <= high]
        self.assertEqual((box["low_whisker"], box["high_whisker"]), (min(inside), max(inside)))
        self.assertEqual(list(box["outliers"]), outliers)
        cleaned = [v for i, v in rows if i not in errors]
        trimmed = [v for v in pay if low <= v <= high]
        for name, values in (("all", pay), ("cleaned", cleaned), ("trimmed", trimmed)):
            want = ref_describe(values)
            for key, value in want.items():
                self.assertAlmostEqual(s[name][key], value, places=6,
                                       msg="%s %s should be %.2f" % (name, key, value))
        self.assertLess(s["trimmed"]["sd"], s["cleaned"]["sd"],
                        "deleting the real high earners makes pay look narrower than it is")

    def test_read_rows(self):
        rows = m.read_rows(self.path)
        self.assertEqual([(r["response_id"], r["base_pay"]) for r in rows], read(self.path))
        self.assertIsInstance(rows[0]["years_experience"], int)


class TestOnCommittedData(OnData, unittest.TestCase):
    path = DATA

    def test_story_numbers(self):
        self.assertEqual(len(m.summarise(self.path)["errors"]), 3)


class TestOnSecondDataset(OnData, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, HERE)
        import make_data
        sys.path.pop(0)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = os.path.join(cls.tmp.name, "salaries.csv")
        make_data.write_csv(cls.path, make_data.build(seed=OTHER_SEED)["salaries"])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_differs(self):
        self.assertNotEqual(read(self.path), read(DATA), "the second dataset should differ")


if __name__ == "__main__":
    unittest.main()
