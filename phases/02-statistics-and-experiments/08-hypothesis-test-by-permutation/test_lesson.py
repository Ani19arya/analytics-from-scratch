"""Tests for lesson 08. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Expected answers are computed here, never read from the solution file:
- exact p-values by listing every split with itertools.combinations, written
  out again below with sums instead of means;
- permutation p-values by a reference shuffle loop written out below.
Your permutation_test may use the random numbers in a different order from the
reference, so its p-value is checked within 5 standard errors of the reference:
5 * sqrt(p * (1 - p) / n_perm), plus 1 / (n_perm + 1) for the +1. With a fixed
seed a correct answer passes on every run.
Everything runs on the committed data AND on a second dataset built in memory
from make_data.build(seed=OTHER_SEED)."""
import ast
import csv
import importlib.util
import itertools
import math
import os
import random
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ORDERS = os.path.join(HERE, "data", "orders.csv")
PILOT = os.path.join(HERE, "data", "pilot.csv")
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")
BANNED = {"statistics", "numpy", "pandas", "scipy", "statsmodels"}
OTHER_SEED = 31
N_PERM = 20000


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


def groups_of(path):
    out = {"control": [], "side_dish": []}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r["order_value"].strip():
                out[r["group"]].append(float(r["order_value"]))
    return out


def hits(d, obs, alternative):
    if alternative == "two-sided":
        return abs(d) >= abs(obs) - 1e-9
    if alternative == "greater":
        return d >= obs - 1e-9
    return d <= obs + 1e-9


def ref_exact(a, b, alternative="two-sided"):
    """Every way to pick len(a) of the pooled values as 'control'. Uses sums, not means."""
    pooled = a + b
    total = sum(pooled)
    na, nb = len(a), len(b)
    obs = (total - sum(a)) / nb - sum(a) / na
    count = splits = 0
    for combo in itertools.combinations(pooled, na):
        s = sum(combo)
        splits += 1
        if hits((total - s) / nb - s / na, obs, alternative):
            count += 1
    return obs, count / splits, splits


def ref_perm(a, b, n_perm, seed, alternative="two-sided"):
    pooled = a + b
    total = sum(pooled)
    na, nb = len(a), len(b)
    obs = (total - sum(a)) / nb - sum(a) / na
    rng = random.Random(seed)
    count = 0
    for _ in range(n_perm):
        rng.shuffle(pooled)
        s = sum(pooled[:na])
        if hits((total - s) / nb - s / na, obs, alternative):
            count += 1
    return obs, (count + 1) / (n_perm + 1)


def tolerance(p, n_perm):
    return 5 * math.sqrt(p * (1 - p) / n_perm) + 1 / (n_perm + 1)


m = load()


class TestRules(unittest.TestCase):
    def test_no_statistics_library(self):
        used = imported_modules(TARGET) & BANNED
        self.assertFalse(used, "Shuffle the labels yourself: remove the import of %s." % ", ".join(sorted(used)))


class TestBasics(unittest.TestCase):
    def test_read_groups_skips_blanks(self):
        got = m.read_groups(ORDERS)
        want = groups_of(ORDERS)
        self.assertEqual(got["control"], want["control"],
                         "control values in file order, as floats, with blank order_value rows skipped (not read as 0)")
        self.assertEqual(got["side_dish"], want["side_dish"])

    def test_mean_diff(self):
        self.assertAlmostEqual(m.mean_diff([1, 2], [3, 4]), 2.0, msg="mean_diff is mean(b) - mean(a): new minus control")
        self.assertAlmostEqual(m.mean_diff([0, 0], [0, 0]), 0.0)
        with self.assertRaises(ValueError):
            m.mean_diff([], [1.0])


class TestExact(unittest.TestCase):
    def test_hand_case_with_ties(self):
        # Splits of {1, 2, 3, 4}: differences 2, 1, 0, 0, -1, -2. Observed is 2.
        self.assertAlmostEqual(m.exact_test([1, 2], [3, 4])["p_value"], 2 / 6,
                               msg="two-sided counts 2 and -2: 2 of the 6 splits")
        self.assertAlmostEqual(m.exact_test([1, 2], [3, 4], "greater")["p_value"], 1 / 6)
        self.assertAlmostEqual(m.exact_test([1, 2], [3, 4], "less")["p_value"], 1.0,
                               msg="'less' counts splits with a difference at or below the observed one")
        self.assertEqual(m.exact_test([1, 2], [3, 4])["splits"], 6)

    def test_all_zero(self):
        self.assertEqual(m.exact_test([0.0, 0.0], [0.0, 0.0])["p_value"], 1.0,
                         "every split ties the observed difference of 0, so all count as extreme")

    def test_pilot(self):
        g = groups_of(PILOT)
        for alt in ("two-sided", "greater", "less"):
            obs, p, splits = ref_exact(g["control"], g["side_dish"], alt)
            r = m.exact_test(g["control"], g["side_dish"], alt)
            self.assertEqual(r["splits"], splits, "10 customers, 5 per group: comb(10, 5) = 252 splits")
            self.assertAlmostEqual(r["observed"], obs, places=9)
            self.assertAlmostEqual(r["p_value"], p, places=12,
                                   msg="exact %s p-value: extreme splits / all splits, no +1" % alt)

    def test_refuses_huge_enumeration(self):
        with self.assertRaises(ValueError, msg="comb(72, 36) splits cannot be listed; raise ValueError"):
            m.exact_test([1.0] * 36, [2.0] * 36)

    def test_errors(self):
        with self.assertRaises(ValueError):
            m.exact_test([], [1.0])
        with self.assertRaises(ValueError):
            m.exact_test([1.0], [2.0], "both")


class TestPermutation(unittest.TestCase):
    def test_plus_one_formula(self):
        r = m.permutation_test([1.0, 2.0, 3.0], [2.0, 5.0, 6.0], n_perm=999, seed=4)
        self.assertEqual(r["n_perm"], 999)
        self.assertAlmostEqual(r["p_value"], (r["extreme"] + 1) / (999 + 1), places=12,
                               msg="p = (extreme + 1) / (n_perm + 1): the observed labelling counts as one of the shuffles")

    def test_never_zero(self):
        a = [float(x) for x in range(1, 9)]
        b = [float(x) for x in range(101, 109)]
        r = m.permutation_test(a, b, n_perm=200, seed=1)
        self.assertGreaterEqual(r["p_value"], 1 / 201,
                                "with 200 shuffles the smallest honest p-value is 1/201, never 0: did you forget the +1?")

    def test_identical_values(self):
        self.assertEqual(m.permutation_test([5.0] * 4, [5.0] * 4, n_perm=50, seed=1)["p_value"], 1.0,
                         "no difference at all: every shuffle is as extreme, so p is 1")

    def test_seed_repeats(self):
        a, b = [1.0, 4.0, 2.0, 8.0], [3.0, 9.0, 7.0, 6.0]
        self.assertEqual(m.permutation_test(a, b, 500, 7), m.permutation_test(a, b, 500, 7),
                         "make one random.Random(seed) inside the function so a seed repeats exactly")

    def test_does_not_change_inputs(self):
        a, b = [1.0, 2.0, 3.0], [4.0, 5.0, 6.0]
        m.permutation_test(a, b, 100, 1)
        self.assertEqual((a, b), ([1.0, 2.0, 3.0], [4.0, 5.0, 6.0]), "shuffle a copy, not the caller's lists")

    def test_errors(self):
        with self.assertRaises(ValueError):
            m.permutation_test([], [1.0])
        with self.assertRaises(ValueError):
            m.permutation_test([1.0], [2.0], n_perm=0)
        with self.assertRaises(ValueError):
            m.permutation_test([1.0], [2.0], alternative="bigger")

    def test_close_to_exact_on_pilot(self):
        g = groups_of(PILOT)
        _, exact_p, _ = ref_exact(g["control"], g["side_dish"])
        r = m.permutation_test(g["control"], g["side_dish"], N_PERM, seed=3)
        self.assertLess(abs(r["p_value"] - exact_p), tolerance(exact_p, N_PERM),
                        "with %d shuffles the p-value should be near the exact %.4f, got %.4f" % (N_PERM, exact_p, r["p_value"]))


class TestOnData(unittest.TestCase):
    def check(self, orders_path, pilot_path):
        g = groups_of(orders_path)
        a, b = g["control"], g["side_dish"]
        for alt in ("two-sided", "greater"):
            obs, p = ref_perm(a, b, N_PERM, 5, alt)
            r = m.permutation_test(a, b, N_PERM, seed=6, alternative=alt)
            self.assertAlmostEqual(r["observed"], obs, places=9, msg="observed is mean(side_dish) - mean(control)")
            self.assertLess(abs(r["p_value"] - p), tolerance(p, N_PERM),
                            "%s p-value should be near %.4f, got %.4f" % (alt, p, r["p_value"]))
        s = m.summarise(orders_path, pilot_path, n_perm=N_PERM, seed=8)
        obs, p = ref_perm(a, b, N_PERM, 9)
        pg = groups_of(pilot_path)
        pobs, pexact, splits = ref_exact(pg["control"], pg["side_dish"])
        self.assertEqual((s["n_control"], s["n_side_dish"]), (len(a), len(b)))
        self.assertAlmostEqual(s["observed"], round(obs, 4), places=4)
        self.assertLess(abs(s["p_two_sided"] - p), tolerance(p, N_PERM) + 1e-4)
        self.assertAlmostEqual(s["pilot_observed"], round(pobs, 4), places=4)
        self.assertAlmostEqual(s["pilot_exact_p"], round(pexact, 4), places=4)
        self.assertEqual(s["pilot_splits"], splits)
        self.assertLess(abs(s["pilot_permutation_p"] - pexact), tolerance(pexact, N_PERM) + 1e-4)
        return obs

    def test_committed_data(self):
        self.check(ORDERS, PILOT)

    def test_second_dataset(self):
        sys.path.insert(0, HERE)
        import make_data
        sys.path.pop(0)
        with tempfile.TemporaryDirectory() as folder:
            make_data.write_all(folder, make_data.build(seed=OTHER_SEED))
            obs = self.check(os.path.join(folder, "orders.csv"), os.path.join(folder, "pilot.csv"))
            self.assertNotAlmostEqual(obs, m.mean_diff(*[groups_of(ORDERS)[k] for k in ("control", "side_dish")]),
                                      msg="the second dataset should differ from the committed one")


if __name__ == "__main__":
    unittest.main()
