"""Tests for lesson 04. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead."""
import csv
import importlib.util
import math
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "pages.csv")
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")

Z975 = 1.959963984540054
Z80 = 0.8416212335729143


def load():
    spec = importlib.util.spec_from_file_location("lesson_module", TARGET)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load()


def reference_n(p1, p2, za=Z975, zb=Z80):
    p_bar = (p1 + p2) / 2
    top = (za * math.sqrt(2 * p_bar * (1 - p_bar))
           + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    return top / (p2 - p1) ** 2


class TestQuantile(unittest.TestCase):
    def test_known_quantiles(self):
        self.assertAlmostEqual(m.z_quantile(0.975), Z975, places=6)
        self.assertAlmostEqual(m.z_quantile(0.80), Z80, places=6)
        self.assertAlmostEqual(m.z_quantile(0.5), 0.0, places=6)

    def test_round_trip(self):
        for p in (0.01, 0.2, 0.9, 0.995):
            self.assertAlmostEqual(m.normal_cdf(m.z_quantile(p)), p, places=9)


class TestSampleSize(unittest.TestCase):
    def test_ten_to_twelve_percent(self):
        n = m.sample_size_per_group(0.10, 0.12)
        self.assertIsInstance(n, int)
        self.assertEqual(n, math.ceil(reference_n(0.10, 0.12)))
        self.assertEqual(n, 3841)

    def test_rounds_up(self):
        n = m.sample_size_per_group(0.20, 0.25)
        self.assertGreaterEqual(n, reference_n(0.20, 0.25))
        self.assertLess(n - reference_n(0.20, 0.25), 1)

    def test_equal_rates_raise(self):
        with self.assertRaises(ValueError):
            m.sample_size_per_group(0.1, 0.1)

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
        self.assertEqual(m.weeks_needed(3841, 5000), 2)
        self.assertEqual(m.weeks_needed(2500, 5000), 1)


class TestPlan(unittest.TestCase):
    def test_plan_matches_reference(self):
        with open(DATA, newline="") as f:
            rows = list(csv.DictReader(f))
        got = m.plan(DATA, 0.10)
        self.assertEqual([r["page"] for r in got], [r["page"] for r in rows])
        for g, r in zip(got, rows):
            base = float(r["baseline_rate"])
            n = math.ceil(reference_n(base, base * 1.10))
            self.assertLessEqual(abs(g["n_per_group"] - n), 1)
            self.assertEqual(g["weeks"], math.ceil(g["n_per_group"] * 2 / int(r["weekly_visitors"])))


if __name__ == "__main__":
    unittest.main()
