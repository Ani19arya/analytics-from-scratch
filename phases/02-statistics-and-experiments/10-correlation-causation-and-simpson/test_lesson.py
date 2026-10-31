"""Tests for lesson 10. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Expected answers are computed here, never read from the solution file. The
reference r uses the one-pass "computational" formula
    r = (n * sum(xy) - sum(x) * sum(y)) / sqrt((n * sum(x^2) - sum(x)^2) * (n * sum(y^2) - sum(y)^2))
which is algebraically the same as the deviations formula in the lesson but
written differently. The within-group r is rebuilt from per-group sums.
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
DATA = os.path.join(HERE, "data", "users.csv")
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")
BANNED = {"statistics", "numpy", "pandas", "scipy", "statsmodels"}
OTHER_SEED = 77


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


def rows_of(path):
    out = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r["workouts_28d"] != "":
                out.append((r["tenure"], int(r["notifications_28d"]), int(r["workouts_28d"])))
    return out


def ref_r(xs, ys):
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxy = sum(x * y for x, y in zip(xs, ys))
    sxx = sum(x * x for x in xs)
    syy = sum(y * y for y in ys)
    return (n * sxy - sx * sy) / math.sqrt((n * sxx - sx * sx) * (n * syy - sy * sy))


def ref_within(rows):
    # within-group covariance and variances from per-group sums
    sums = {}
    for t, x, y in rows:
        s = sums.setdefault(t, [0, 0, 0, 0, 0, 0])
        s[0] += 1; s[1] += x; s[2] += y; s[3] += x * y; s[4] += x * x; s[5] += y * y
    cxy = cxx = cyy = 0.0
    for n, sx, sy, sxy, sxx, syy in sums.values():
        cxy += sxy - sx * sy / n
        cxx += sxx - sx * sx / n
        cyy += syy - sy * sy / n
    return cxy / math.sqrt(cxx * cyy)


m = load()


class TestRules(unittest.TestCase):
    def test_no_statistics_library(self):
        used = imported_modules(TARGET) & BANNED
        self.assertFalse(used, "Write r yourself: remove the import of %s." % ", ".join(sorted(used)))


class TestPearson(unittest.TestCase):
    def test_hand_example(self):
        xs, ys = [2, 4, 6, 8, 10], [3, 7, 5, 11, 9]
        self.assertAlmostEqual(m.pearson_r(xs, ys), ref_r(xs, ys), places=12)
        self.assertAlmostEqual(m.pearson_r(xs, ys), 0.8, places=12, msg="r for this toy example is exactly 0.8")

    def test_perfect_and_symmetric(self):
        self.assertAlmostEqual(m.pearson_r([1, 2, 3], [10, 20, 30]), 1.0, places=12)
        self.assertAlmostEqual(m.pearson_r([1, 2, 3], [5, 3, 1]), -1.0, places=12)
        self.assertAlmostEqual(m.pearson_r([1, 5, 2, 8], [3, 1, 4, 1]), m.pearson_r([3, 1, 4, 1], [1, 5, 2, 8]), places=12,
                               msg="r(x, y) must equal r(y, x)")

    def test_unit_free(self):
        xs, ys = [1, 4, 2, 7, 5], [10, 30, 25, 40, 50]
        self.assertAlmostEqual(m.pearson_r(xs, ys), m.pearson_r([100 * x + 3 for x in xs], ys), places=12,
                               msg="r does not change when x is rescaled or shifted")

    def test_curve_has_zero_r(self):
        xs = [-2, -1, 0, 1, 2]
        self.assertAlmostEqual(m.pearson_r(xs, [x * x for x in xs]), 0.0, places=12,
                               msg="y = x squared is a perfect relationship with r = 0: r only sees straight lines")

    def test_errors(self):
        for xs, ys in (([], []), ([1], [2]), ([1, 2], [1, 2, 3]), ([3, 3, 3], [1, 2, 3]), ([1, 2, 3], [0, 0, 0])):
            with self.assertRaises(ValueError, msg="pearson_r(%r, %r) should raise ValueError" % (xs, ys)):
                m.pearson_r(xs, ys)


class TestGroups(unittest.TestCase):
    USERS = [
        {"tenure": "new", "notifications": 1, "workouts": 2},
        {"tenure": "new", "notifications": 2, "workouts": 1},
        {"tenure": "old", "notifications": 5, "workouts": 6},
        {"tenure": "old", "notifications": 6, "workouts": 5},
        {"tenure": "solo", "notifications": 9, "workouts": 9},
        {"tenure": "flat", "notifications": 3, "workouts": 4},
        {"tenure": "flat", "notifications": 3, "workouts": 7},
    ]

    def test_r_by_group(self):
        got = m.r_by_group(self.USERS)
        self.assertEqual(sorted(got), ["flat", "new", "old", "solo"])
        self.assertAlmostEqual(got["new"]["r"], -1.0, places=12)
        self.assertAlmostEqual(got["old"]["r"], -1.0, places=12)
        self.assertEqual(got["new"]["n"], 2)
        self.assertIsNone(got["solo"]["r"], "one user: r is undefined, use None")
        self.assertIsNone(got["flat"]["r"], "notifications do not vary in this group: r is undefined, use None")

    def test_within_group_reverses(self):
        users = self.USERS[:4]
        overall = m.pearson_r([u["notifications"] for u in users], [u["workouts"] for u in users])
        self.assertGreater(overall, 0)
        self.assertAlmostEqual(m.within_group_r(users), -1.0, places=12,
                               msg="subtract each group's own means first, then correlate")

    def test_is_simpson(self):
        self.assertTrue(m.is_simpson(0.6, [-0.2, -0.3]))
        self.assertTrue(m.is_simpson(-0.4, [0.1, None, 0.2]), "skip groups whose r is None")
        self.assertFalse(m.is_simpson(0.6, [-0.2, 0.1]), "every group must point the other way")
        self.assertFalse(m.is_simpson(0.6, [-0.2, 0.0]), "0 has no direction, so it is not a reversal")
        self.assertFalse(m.is_simpson(0.0, [-0.2, -0.3]))
        self.assertFalse(m.is_simpson(0.5, [None]), "no group r left: nothing to compare")


class TestOnData(unittest.TestCase):
    def check(self, path):
        rows = rows_of(path)
        got = m.read_users(path)
        self.assertEqual([(u["tenure"], u["notifications"], u["workouts"]) for u in got], rows,
                         "one dict per user in file order, whole numbers, users with a blank workouts_28d skipped")
        s = m.summarise(path)
        overall = ref_r([r[1] for r in rows], [r[2] for r in rows])
        self.assertEqual(s["n"], len(rows))
        self.assertAlmostEqual(s["overall_r"], round(overall, 4), places=4)
        group_rs = []
        for t in sorted({r[0] for r in rows}):
            members = [r for r in rows if r[0] == t]
            want = ref_r([r[1] for r in members], [r[2] for r in members])
            group_rs.append(want)
            self.assertEqual(s["by_tenure"][t]["n"], len(members))
            self.assertAlmostEqual(s["by_tenure"][t]["r"], round(want, 4), places=4,
                                   msg="r for the %s group" % t)
        self.assertAlmostEqual(s["within_r"], round(ref_within(rows), 4), places=4)
        reversed_ = all(g * overall < 0 for g in group_rs)
        self.assertEqual(s["simpson"], reversed_)
        return overall

    def test_committed_data(self):
        self.check(DATA)

    def test_second_dataset(self):
        sys.path.insert(0, HERE)
        import make_data
        sys.path.pop(0)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "users.csv")
            make_data.write_csv(path, make_data.build(seed=OTHER_SEED)["users"])
            overall = self.check(path)
            self.assertNotAlmostEqual(overall, m.summarise(DATA)["overall_r"], places=4,
                                      msg="the second dataset should differ")


if __name__ == "__main__":
    unittest.main()
