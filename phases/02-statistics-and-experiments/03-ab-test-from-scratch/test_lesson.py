"""Tests for lesson 03. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead."""
import csv
import importlib.util
import math
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "experiment.csv")
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")


def load():
    spec = importlib.util.spec_from_file_location("lesson_module", TARGET)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load()


def reference(ca, na, cb, nb):
    pool = (ca + cb) / (na + nb)
    se = math.sqrt(pool * (1 - pool) * (1 / na + 1 / nb))
    z = (cb / nb - ca / na) / se
    p = math.erfc(abs(z) / math.sqrt(2))
    return pool, se, z, p


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
        self.assertAlmostEqual(r["se"], se, places=9)
        self.assertAlmostEqual(r["z"], z, places=6)
        self.assertAlmostEqual(r["p_value"], p, places=6)
        self.assertAlmostEqual(r["z"], 2.974, places=2)

    def test_no_difference(self):
        r = m.two_proportion_ztest(50, 500, 50, 500)
        self.assertAlmostEqual(r["z"], 0.0)
        self.assertAlmostEqual(r["p_value"], 1.0)

    def test_sign_follows_b_minus_a(self):
        r = m.two_proportion_ztest(260, 2000, 200, 2000)
        self.assertLess(r["z"], 0)

    def test_decide(self):
        self.assertEqual(m.decide({"p_value": 0.01, "lift": 0.02}), "ship")
        self.assertEqual(m.decide({"p_value": 0.20, "lift": 0.02}), "do not ship")
        self.assertEqual(m.decide({"p_value": 0.01, "lift": -0.02}), "do not ship")
        self.assertEqual(m.decide({"p_value": 0.03, "lift": 0.02}, alpha=0.01), "do not ship")


class TestOnData(unittest.TestCase):
    def test_counts(self):
        expected = {"A": [0, 0], "B": [0, 0]}
        with open(DATA, newline="") as f:
            for row in csv.DictReader(f):
                expected[row["variant"]][0] += int(row["converted"])
                expected[row["variant"]][1] += 1
        got = m.count_conversions(DATA)
        self.assertEqual(tuple(got["A"]), tuple(expected["A"]))
        self.assertEqual(tuple(got["B"]), tuple(expected["B"]))

    def test_experiment_result(self):
        got = m.count_conversions(DATA)
        (ca, na), (cb, nb) = got["A"], got["B"]
        r = m.two_proportion_ztest(ca, na, cb, nb)
        _, _, z, p = reference(ca, na, cb, nb)
        self.assertAlmostEqual(r["z"], z, places=6)
        self.assertAlmostEqual(r["p_value"], p, places=6)
        self.assertEqual(m.decide(r), "ship" if (p < 0.05 and z > 0) else "do not ship")


if __name__ == "__main__":
    unittest.main()
