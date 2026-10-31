"""Tests for lesson 15. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Expected answers are computed here by a different route, never read from the
solution file:
- theta from the least squares slope written with raw sums,
  (n sum xy - sum x sum y) / (n sum x^2 - (sum x)^2), and checked to be the
  value that minimises the variance of y - theta x (nudging it either way
  must not help);
- the variance reduction from the observed variances of the adjusted and raw
  spend in each group, compared with the squared correlation it should be
  close to;
- and, without any formula, from an A/A simulation: shuffle the group labels
  1,000 times with a fixed seed and compare the spread of the CUPED estimates
  with the spread of the raw estimates.
Everything runs on the committed data AND on a second dataset built in memory
from make_data.build(seed=OTHER_SEED)."""
import ast
import csv
import importlib.util
import math
import os
import random
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
USERS = os.path.join(HERE, "data", "users.csv")
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")
BANNED = {"statistics", "numpy", "pandas", "scipy", "statsmodels"}
OTHER_SEED = 33
SHUFFLES = 1000


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


def ref_rows(path):
    with open(path, newline="") as f:
        return [(r["variant"], float(r["pre_spend"]) if r["pre_spend"] else None, float(r["spend"]),
                 int(r["test_sessions"])) for r in csv.DictReader(f)]


def ref_slope(xs, ys):
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxy = sum(x * y for x, y in zip(xs, ys))
    sxx = sum(x * x for x in xs)
    return (n * sxy - sx * sy) / (n * sxx - sx * sx)


def ref_var(v):
    n = len(v)
    s, ss = sum(v), sum(x * x for x in v)
    return (ss - s * s / n) / (n - 1)


def ref_corr2(xs, ys):
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    num = n * sum(x * y for x, y in zip(xs, ys)) - sx * sy
    return num * num / ((n * sum(x * x for x in xs) - sx * sx) * (n * sum(y * y for y in ys) - sy * sy))


def ref_filled(rows, col):
    xs = [r[col] for r in rows]
    present = [x for x in xs if x is not None]
    fill = sum(present) / len(present)
    return [fill if x is None else x for x in xs]


def ref_se(groups):
    return math.sqrt(sum(ref_var(g) / len(g) for g in groups))


m = load()


class TestRules(unittest.TestCase):
    def test_no_statistics_library(self):
        used = imported_modules(TARGET) & BANNED
        self.assertFalse(used, "Write CUPED yourself: remove the import of %s." % ", ".join(sorted(used)))


class TestPieces(unittest.TestCase):
    def test_fill_missing(self):
        self.assertEqual(list(m.fill_missing([2.0, None, 4.0, None])), [2.0, 3.0, 4.0, 3.0],
                         "fill a missing value with the mean of the values that are present")
        self.assertEqual(list(m.fill_missing([1.0, 5.0])), [1.0, 5.0])
        with self.assertRaises(ValueError):
            m.fill_missing([None, None])

    def test_theta(self):
        xs = [1.0, 2.0, 3.0, 4.0, 10.0]
        ys = [2.5, 3.0, 7.5, 8.0, 21.0]
        self.assertAlmostEqual(m.theta(xs, ys), ref_slope(xs, ys), places=12, msg="theta = cov(x, y) / var(x)")
        self.assertAlmostEqual(m.theta([1.0, 2.0, 3.0], [5.0, 5.0, 5.0]), 0.0, places=12,
                               msg="y does not vary: nothing to remove")
        self.assertAlmostEqual(m.theta([1.0, 2.0, 3.0], [-2.0, -4.0, -6.0]), -2.0, places=12)
        with self.assertRaises(ValueError):
            m.theta([3.0, 3.0, 3.0], [1.0, 2.0, 3.0])
        with self.assertRaises(ValueError):
            m.theta([1.0], [2.0])

    def test_cuped_adjust(self):
        xs = [0.0, 10.0, 20.0]
        ys = [5.0, 12.0, 25.0]
        got = list(m.cuped_adjust(xs, ys, 0.5))
        self.assertEqual([round(v, 9) for v in got], [10.0, 12.0, 20.0], "y - theta * (x - mean(x))")
        self.assertAlmostEqual(sum(got) / 3, sum(ys) / 3, places=12, msg="the adjustment must not move the mean")
        self.assertEqual(list(m.cuped_adjust(xs, ys, 0.0)), ys)

    def test_diff_in_means(self):
        c = [10.0, 12.0, 9.0, 14.0, 11.0]
        t = [13.0, 15.0, 12.0, 18.0]
        got = m.diff_in_means(c, t)
        se = ref_se([c, t])
        diff = sum(t) / 4 - sum(c) / 5
        self.assertAlmostEqual(got["diff"], diff, places=12)
        self.assertAlmostEqual(got["se"], se, places=12, msg="unpooled: sqrt(var_c / n_c + var_t / n_t), n - 1 variances")
        self.assertAlmostEqual(got["p_value"], math.erfc(abs(diff / se) / math.sqrt(2)), places=9)
        self.assertAlmostEqual(got["ci"][0], diff - 1.959963984540054 * se, places=6)
        flat = m.diff_in_means([3.0, 3.0], [3.0, 3.0])
        self.assertEqual((flat["diff"], flat["p_value"]), (0.0, 1.0))
        with self.assertRaises(ValueError):
            m.diff_in_means([1.0], [2.0, 3.0])


class TestOnData(unittest.TestCase):
    def check(self, path):
        rows = ref_rows(path)
        got = m.read_users(path)
        self.assertEqual([(u["variant"], u["pre_spend"], u["spend"], u["test_sessions"]) for u in got], rows,
                         "one dict per user; a blank pre_spend is None, not 0")
        s = m.summarise(path)
        xs = ref_filled(rows, 1)
        ys = [r[2] for r in rows]
        t = ref_slope(xs, ys)
        self.assertAlmostEqual(s["theta"], t, places=9, msg="theta from every user, both groups together, missing pre_spend filled with the mean")
        mx = sum(xs) / len(xs)

        def adjusted_var(th):
            return ref_var([y - th * (x - mx) for x, y in zip(xs, ys)])

        best = adjusted_var(s["theta"])
        for nudge in (-0.05, -0.01, 0.01, 0.05):
            self.assertLess(best, adjusted_var(s["theta"] + nudge), "theta should give the smallest possible variance")
        adj = [y - t * (x - mx) for x, y in zip(xs, ys)]
        raw_g = [[y for r, y in zip(rows, ys) if r[0] == g] for g in ("control", "shelf")]
        adj_g = [[a for r, a in zip(rows, adj) if r[0] == g] for g in ("control", "shelf")]
        self.assertEqual(dict(s["n"]), {"control": len(raw_g[0]), "shelf": len(raw_g[1])})
        self.assertEqual(s["missing_covariate"], sum(1 for r in rows if r[1] is None))
        self.assertAlmostEqual(s["raw"]["diff"], sum(raw_g[1]) / len(raw_g[1]) - sum(raw_g[0]) / len(raw_g[0]), places=9)
        self.assertAlmostEqual(s["cuped"]["diff"], sum(adj_g[1]) / len(adj_g[1]) - sum(adj_g[0]) / len(adj_g[0]), places=9)
        self.assertAlmostEqual(s["raw"]["se"], ref_se(raw_g), places=9)
        self.assertAlmostEqual(s["cuped"]["se"], ref_se(adj_g), places=9, msg="the CUPED SE comes from the adjusted spend")
        observed = 1 - ref_se(adj_g) ** 2 / ref_se(raw_g) ** 2
        self.assertAlmostEqual(s["variance_reduction"], observed, places=9,
                               msg="variance reduction: 1 - (CUPED SE / raw SE)^2")
        self.assertAlmostEqual(s["users_needed_share"], 1 - observed, places=9)
        self.assertLess(abs(observed - ref_corr2(xs, ys)), 0.05,
                        "the variance reduction should be close to the squared correlation of pre_spend and spend")
        rng = random.Random(1)
        labels = [r[0] for r in rows]
        raw_est, cup_est = [], []
        for _ in range(SHUFFLES):
            rng.shuffle(labels)
            sums = {"control": [0.0, 0.0, 0], "shelf": [0.0, 0.0, 0]}
            for g, y, a in zip(labels, ys, adj):
                cell = sums[g]
                cell[0] += y
                cell[1] += a
                cell[2] += 1
            c, sh = sums["control"], sums["shelf"]
            raw_est.append(sh[0] / sh[2] - c[0] / c[2])
            cup_est.append(sh[1] / sh[2] - c[1] / c[2])
        simulated = 1 - ref_var(cup_est) / ref_var(raw_est)
        self.assertLess(abs(s["variance_reduction"] - simulated), 0.06,
                        "in A/A shuffles CUPED estimates should spread less by about the reported reduction (%.3f vs %.3f)"
                        % (s["variance_reduction"], simulated))
        self.assertLess(abs(sum(cup_est) / SHUFFLES), 3 * math.sqrt(ref_var(cup_est) / SHUFFLES),
                        "CUPED must not bias the estimate: A/A shuffles should average about 0")
        trap = m.summarise(path, covariate="test_sessions")
        xs2 = ref_filled(rows, 3)
        self.assertAlmostEqual(trap["theta"], ref_slope(xs2, ys), places=9, msg="covariate='test_sessions' uses that column")
        with self.assertRaises(ValueError):
            m.summarise(path, covariate="spend")
        return s

    def test_committed_data(self):
        s = self.check(USERS)
        self.assertGreater(s["raw"]["p_value"], 0.05, "on the lesson data the raw test is not significant")
        self.assertLess(s["cuped"]["p_value"], 0.01, "on the lesson data the CUPED test is")

    def test_second_dataset(self):
        sys.path.insert(0, HERE)
        import make_data
        sys.path.pop(0)
        with tempfile.TemporaryDirectory() as folder:
            make_data.write_all(folder, make_data.build(seed=OTHER_SEED))
            s = self.check(os.path.join(folder, "users.csv"))
            self.assertNotEqual(round(s["theta"], 6), round(m.summarise(USERS)["theta"], 6), "the second dataset should differ")


if __name__ == "__main__":
    unittest.main()
