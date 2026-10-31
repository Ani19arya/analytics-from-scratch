"""Tests for lesson 03. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Expected answers come from plain formulas here (math.erfc, written out),
never from the solution file. The pipeline is checked on the committed data
AND on a second dataset built in memory with another seed."""
import ast
import csv
import importlib.util
import math
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "experiment.csv")
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")
BANNED = {"statistics", "numpy", "pandas", "scipy", "statsmodels"}
OTHER_SEED = 11


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


def reference(ca, na, cb, nb):
    pool = (ca + cb) / (na + nb)
    se = math.sqrt(pool * (1 - pool) * (1 / na + 1 / nb))
    z = (cb / nb - ca / na) / se
    p = math.erfc(abs(z) / math.sqrt(2))
    return pool, se, z, p


def reference_ci(ca, na, cb, nb):
    pa, pb = ca / na, cb / nb
    half = 1.96 * math.sqrt(pa * (1 - pa) / na + pb * (1 - pb) / nb)
    return pb - pa - half, pb - pa + half


def reference_srm(na, nb):
    e = (na + nb) / 2
    chi2 = ((na - e) ** 2 + (nb - e) ** 2) / e
    return chi2, math.erfc(math.sqrt(chi2 / 2))


def count_rows(path):
    expected = {"A": [0, 0], "B": [0, 0]}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            expected[row["variant"]][0] += int(row["converted"])
            expected[row["variant"]][1] += 1
    return expected


m = load()


class TestRules(unittest.TestCase):
    def test_no_statistics_library(self):
        used = imported_modules(TARGET) & BANNED
        self.assertFalse(used, "Write the test yourself: remove the import of %s." % ", ".join(sorted(used)))


class TestNormal(unittest.TestCase):
    def test_cdf_known_points(self):
        self.assertAlmostEqual(m.normal_cdf(0), 0.5, places=9)
        self.assertAlmostEqual(m.normal_cdf(1.96), 0.9750, places=4)
        self.assertAlmostEqual(m.normal_cdf(-1.96), 0.0250, places=4)


class TestZTest(unittest.TestCase):
    def test_known_example(self):
        r = m.two_proportion_ztest(200, 2000, 260, 2000)
        pool, se, z, p = reference(200, 2000, 260, 2000)
        self.assertAlmostEqual(r["p_a"], 0.10)
        self.assertAlmostEqual(r["p_b"], 0.13)
        self.assertAlmostEqual(r["lift"], 0.03)
        self.assertAlmostEqual(r["p_pool"], pool)
        self.assertAlmostEqual(r["se"], se, places=9, msg="use the POOLED rate in the test's standard error")
        self.assertAlmostEqual(r["z"], z, places=6)
        self.assertAlmostEqual(r["p_value"], p, places=6, msg="two-sided: double the tail beyond |z|")
        self.assertAlmostEqual(r["z"], 2.974, places=2)

    def test_no_difference(self):
        r = m.two_proportion_ztest(50, 500, 50, 500)
        self.assertAlmostEqual(r["z"], 0.0)
        self.assertAlmostEqual(r["p_value"], 1.0)

    def test_zero_conversions_everywhere(self):
        r = m.two_proportion_ztest(0, 100, 0, 100)
        self.assertEqual((r["z"], r["p_value"]), (0.0, 1.0), "standard error 0: return z 0.0 and p 1.0, do not divide")

    def test_empty_group_raises(self):
        with self.assertRaises(ValueError):
            m.two_proportion_ztest(0, 0, 5, 50)

    def test_sign_follows_b_minus_a(self):
        r = m.two_proportion_ztest(260, 2000, 200, 2000)
        self.assertLess(r["z"], 0)

    def test_decide(self):
        self.assertEqual(m.decide({"p_value": 0.01, "lift": 0.02}), "ship")
        self.assertEqual(m.decide({"p_value": 0.20, "lift": 0.02}), "do not ship")
        self.assertEqual(m.decide({"p_value": 0.01, "lift": -0.02}), "do not ship", "a significant drop is not a win")
        self.assertEqual(m.decide({"p_value": 0.03, "lift": 0.02}, alpha=0.01), "do not ship")
        self.assertEqual(m.decide({"p_value": 0.05, "lift": 0.02}), "do not ship", "p must be strictly below alpha")
        self.assertEqual(m.decide({"p_value": 0.001, "lift": 0.001}, min_lift=0.005), "do not ship",
                         "significant but smaller than the smallest lift worth shipping")


class TestSrmAndInterval(unittest.TestCase):
    def test_srm_balanced(self):
        r = m.srm_check(500, 500)
        self.assertAlmostEqual(r["chi2"], 0.0)
        self.assertAlmostEqual(r["p_value"], 1.0)

    def test_srm_known(self):
        chi2, p = reference_srm(1050, 950)
        r = m.srm_check(1050, 950)
        self.assertAlmostEqual(r["chi2"], chi2, places=9)
        self.assertAlmostEqual(r["p_value"], p, places=6)

    def test_srm_uneven_plan(self):
        r = m.srm_check(900, 100, expected_share_a=0.9)
        self.assertAlmostEqual(r["chi2"], 0.0, msg="a planned 90/10 split that came out 90/10 is fine")

    def test_srm_empty_raises(self):
        with self.assertRaises(ValueError):
            m.srm_check(0, 0)

    def test_diff_ci_known(self):
        low, high = m.diff_ci(200, 2000, 260, 2000)
        ref = reference_ci(200, 2000, 260, 2000)
        self.assertAlmostEqual(low, ref[0], places=9, msg="the interval uses the UNPOOLED standard error")
        self.assertAlmostEqual(high, ref[1], places=9)

    def test_diff_ci_zero(self):
        self.assertEqual(tuple(m.diff_ci(0, 10, 0, 10)), (0, 0))


class TestOnData(unittest.TestCase):
    def check_pipeline(self, path):
        expected = count_rows(path)
        got = m.count_conversions(path)
        self.assertEqual(tuple(got["A"]), tuple(expected["A"]), "count conversions AND users per variant")
        self.assertEqual(tuple(got["B"]), tuple(expected["B"]))
        (ca, na), (cb, nb) = expected["A"], expected["B"]
        r = m.two_proportion_ztest(ca, na, cb, nb)
        _, _, z, p = reference(ca, na, cb, nb)
        self.assertAlmostEqual(r["z"], z, places=6)
        self.assertAlmostEqual(r["p_value"], p, places=6)
        self.assertEqual(m.decide(r), "ship" if (p < 0.05 and z > 0) else "do not ship")
        low, high = m.diff_ci(ca, na, cb, nb)
        ref = reference_ci(ca, na, cb, nb)
        self.assertAlmostEqual(low, ref[0], places=9)
        self.assertAlmostEqual(high, ref[1], places=9)
        chi2, srm_p = reference_srm(na, nb)
        s = m.srm_check(na, nb)
        self.assertAlmostEqual(s["chi2"], chi2, places=9)
        self.assertAlmostEqual(s["p_value"], srm_p, places=6)
        return expected

    def test_committed_data(self):
        self.check_pipeline(DATA)

    def test_second_dataset(self):
        sys.path.insert(0, HERE)
        import make_data
        sys.path.pop(0)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "experiment.csv")
            make_data.write_csv(path, make_data.build(seed=OTHER_SEED)["experiment"])
            counts = self.check_pipeline(path)
            self.assertNotEqual(counts, count_rows(DATA), "the second dataset should differ")


if __name__ == "__main__":
    unittest.main()
