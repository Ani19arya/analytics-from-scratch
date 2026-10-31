"""Tests for lesson 14. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Expected answers are computed here by a different route, never read from the
solution file:
- the delta method variance from the residual form
  sum((r_i - R * a_i)^2) / (n * (n - 1) * mean_a^2), which is the same
  quantity written another way;
- and, independently of any formula, the standard error of the difference
  from a cluster bootstrap: resample whole users, with replacement, within
  each group, 2,000 times, with a fixed seed. The delta method must agree with
  it to within 10%.
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
OTHER_SEED = 21
N_BOOT = 2000


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


def ref_groups(path):
    groups = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            groups.setdefault(r["variant"], []).append((int(r["applications"]), int(r["replies"])))
    return groups


def ref_ratio(pairs):
    return sum(r for _, r in pairs) / sum(a for a, _ in pairs)


def ref_delta_var(pairs):
    n = len(pairs)
    big_r = ref_ratio(pairs)
    mean_a = sum(a for a, _ in pairs) / n
    return sum((r - big_r * a) ** 2 for a, r in pairs) / (n * (n - 1) * mean_a ** 2)


def ref_bootstrap_se(control, treatment, n_boot, seed):
    rng = random.Random(seed)
    diffs = []
    for _ in range(n_boot):
        c = [control[rng.randrange(len(control))] for _ in control]
        t = [treatment[rng.randrange(len(treatment))] for _ in treatment]
        diffs.append(ref_ratio(t) - ref_ratio(c))
    mean = sum(diffs) / n_boot
    return math.sqrt(sum((d - mean) ** 2 for d in diffs) / (n_boot - 1))


def ref_p(z):
    return math.erfc(abs(z) / math.sqrt(2))


m = load()


class TestRules(unittest.TestCase):
    def test_no_statistics_library(self):
        used = imported_modules(TARGET) & BANNED
        self.assertFalse(used, "Write the delta method yourself: remove the import of %s." % ", ".join(sorted(used)))


class TestPieces(unittest.TestCase):
    def test_ratio(self):
        self.assertAlmostEqual(m.ratio([(10, 1), (0, 0), (2, 2)]), 0.25,
                               msg="total replies 3 over total applications 12, not the mean of per-user rates")
        with self.assertRaises(ValueError):
            m.ratio([(0, 0), (0, 0)])

    def test_naive_var(self):
        self.assertAlmostEqual(m.naive_var([(10, 1), (2, 2)]), 0.25 * 0.75 / 12, places=12,
                               msg="R (1 - R) / total applications")

    def test_delta_var_hand_cases(self):
        pairs = [(4, 1), (1, 0), (10, 1), (0, 0), (3, 3)]
        self.assertAlmostEqual(m.delta_var(pairs), ref_delta_var(pairs), places=12,
                               msg="(var_r - 2 R cov + R^2 var_a) / (n mean_a^2), sample (n - 1) variances, users with 0 applications included")
        ones = [(1, 1)] * 30 + [(1, 0)] * 70
        self.assertAlmostEqual(m.delta_var(ones), 0.3 * 0.7 / 99, places=12,
                               msg="one application per user: the delta method is the binomial variance with n - 1")
        same = [(5, 1)] * 20
        self.assertAlmostEqual(m.delta_var(same), 0.0, places=12, msg="identical users: no variation in the ratio")
        with self.assertRaises(ValueError):
            m.delta_var([(5, 1)])
        with self.assertRaises(ValueError):
            m.delta_var([(0, 0), (0, 0), (0, 0)])

    def test_compare_shape(self):
        c = [(3, 1), (1, 0), (6, 2), (2, 1)]
        t = [(5, 1), (2, 0), (8, 1), (1, 1)]
        got = m.compare(c, t)
        diff = ref_ratio(t) - ref_ratio(c)
        se = math.sqrt(ref_delta_var(c) + ref_delta_var(t))
        self.assertAlmostEqual(got["diff"], diff, places=12, msg="treatment ratio minus control ratio")
        self.assertAlmostEqual(got["se"], se, places=12, msg="the two groups are independent: add their variances")
        self.assertAlmostEqual(got["z"], diff / se, places=12)
        self.assertAlmostEqual(got["p_value"], ref_p(diff / se), places=9)
        self.assertAlmostEqual(got["ci"][0], diff - 1.959963984540054 * se, places=6)
        self.assertAlmostEqual(got["ci"][1], diff + 1.959963984540054 * se, places=6)
        flat = m.compare([(2, 1)] * 5, [(2, 1)] * 5)
        self.assertEqual((flat["se"], flat["p_value"]), (0.0, 1.0), "no variation and no difference: p = 1")
        with self.assertRaises(ValueError):
            m.compare(c, t, method="bootstrap")


class TestOnData(unittest.TestCase):
    def check(self, path):
        groups = ref_groups(path)
        got_groups = m.read_users(path)
        self.assertEqual({k: [tuple(p) for p in v] for k, v in got_groups.items()}, groups,
                         "one (applications, replies) pair per user, grouped by variant, in file order")
        c, t = groups["control"], groups["quick_apply"]
        s = m.summarise(path)
        self.assertEqual(dict(s["users"]), {"control": len(c), "quick_apply": len(t)})
        self.assertEqual(dict(s["applications"]), {"control": sum(a for a, _ in c), "quick_apply": sum(a for a, _ in t)})
        diff = ref_ratio(t) - ref_ratio(c)
        se_delta = math.sqrt(ref_delta_var(c) + ref_delta_var(t))
        se_naive = math.sqrt(sum(ref_ratio(g) * (1 - ref_ratio(g)) / sum(a for a, _ in g) for g in (c, t)))
        for key, se in (("delta", se_delta), ("naive", se_naive)):
            self.assertAlmostEqual(s[key]["diff"], diff, places=12)
            self.assertAlmostEqual(s[key]["se"], se, places=12, msg="%s standard error of the difference" % key)
            self.assertAlmostEqual(s[key]["p_value"], ref_p(diff / se), places=9)
        self.assertAlmostEqual(s["design_effect"], (se_delta / se_naive) ** 2, places=9,
                               msg="design effect: delta variance over naive variance")
        boot = ref_bootstrap_se(c, t, N_BOOT, seed=5)
        self.assertLess(abs(s["delta"]["se"] / boot - 1), 0.10,
                        "the delta method SE should be within 10%% of a cluster bootstrap SE (%.5f vs %.5f)"
                        % (s["delta"]["se"], boot))
        self.assertGreater(boot / s["naive"]["se"], 1.3,
                           "the naive SE treats applications as independent and should be clearly too small")
        return s

    def test_committed_data(self):
        s = self.check(USERS)
        self.assertLess(s["naive"]["p_value"], 0.05, "on the lesson data the naive test calls the drop significant")
        self.assertGreater(s["delta"]["p_value"], 0.05, "on the lesson data the delta method does not")

    def test_second_dataset(self):
        sys.path.insert(0, HERE)
        import make_data
        sys.path.pop(0)
        with tempfile.TemporaryDirectory() as folder:
            make_data.write_all(folder, make_data.build(seed=OTHER_SEED))
            s = self.check(os.path.join(folder, "users.csv"))
            self.assertNotEqual(s["applications"], m.summarise(USERS)["applications"], "the second dataset should differ")


if __name__ == "__main__":
    unittest.main()
