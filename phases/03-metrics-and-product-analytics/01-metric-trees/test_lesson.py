"""Tests for lesson 01: metric trees. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Every expected number is computed here in plain Python, never read from the solution.
The tests run on the committed data and on a second dataset built with another seed."""
import csv
import importlib.util
import math
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "daily_channels.csv")
SPLIT = "2026-10-12"
OTHER_SEED = 7
CHANNELS = ("search", "email", "paid_social")
FACTORS = ("visitors", "conversion", "aov")
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
sys.path.insert(0, HERE)
import make_data  # noqa: E402


def raw_sums(path, channel=None):
    sums = {"prior": [0, 0, 0.0], "current": [0, 0, 0.0]}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if channel and row["channel"] != channel:
                continue
            k = "prior" if row["date"] < SPLIT else "current"
            sums[k][0] += int(row["visitors"])
            sums[k][1] += int(row["orders"])
            sums[k][2] += float(row["revenue"])
    return sums


def reference_effects(s):
    """A second route to the same split: when revenue changed, LMDI equals
    total x ln(f1/f0) / ln(R1/R0). Factors come straight from the sums."""
    (v0, o0, r0), (v1, o1, r1) = s["prior"], s["current"]
    f0 = {"visitors": v0, "conversion": o0 / v0, "aov": r0 / o0}
    f1 = {"visitors": v1, "conversion": o1 / v1, "aov": r1 / o1}
    total = r1 - r0
    return {f: total * math.log(f1[f] / f0[f]) / math.log(r1 / r0) for f in FACTORS}, total


class TestTree(unittest.TestCase):
    def test_build_tree(self):
        t = m.build_tree(1000, 40, 2400.0)
        self.assertAlmostEqual(t["conversion"], 0.04)
        self.assertAlmostEqual(t["aov"], 60.0)
        self.assertAlmostEqual(t["visitors"] * t["conversion"] * t["aov"], t["revenue"])

    def test_zero_orders(self):
        t = m.build_tree(500, 0, 0.0)
        self.assertEqual(t["aov"], 0.0, "aov must be 0.0 when there are no orders, not a division error")
        self.assertEqual(t["conversion"], 0.0)
        t = m.build_tree(0, 0, 0.0)
        self.assertEqual(t["conversion"], 0.0, "conversion must be 0.0 when there are no visitors")

    def test_log_mean(self):
        self.assertAlmostEqual(m.log_mean(2.0, 1.0), 1.0 / math.log(2.0))
        self.assertAlmostEqual(m.log_mean(1.0, 2.0), 1.0 / math.log(2.0), msg="L(a, b) must equal L(b, a)")
        self.assertEqual(m.log_mean(2400.0, 2400.0), 2400.0, "L(a, a) is a: handle equal values without dividing by zero")

    def test_decompose_simple(self):
        prior = m.build_tree(1000, 40, 2400.0)
        current = m.build_tree(1000, 20, 1200.0)  # only conversion halved
        e = m.decompose(prior, current)
        self.assertAlmostEqual(e["total"], -1200.0)
        self.assertAlmostEqual(e["conversion"], -1200.0)
        self.assertAlmostEqual(e["visitors"], 0.0)
        self.assertAlmostEqual(e["aov"], 0.0)
        self.assertEqual(m.main_driver(e), "conversion")

    def test_decompose_no_change(self):
        t = m.build_tree(1000, 40, 2400.0)
        e = m.decompose(t, dict(t))
        self.assertEqual((e["total"], e["visitors"], e["conversion"], e["aov"]), (0.0, 0.0, 0.0, 0.0))

    def test_flat_revenue_with_moving_factors(self):
        # Visitors +10%, conversion -9.1%, revenue flat. The effects are not 0: they cancel.
        prior = m.build_tree(1000, 40, 2400.0)
        current = m.build_tree(1100, 40, 2400.0)
        e = m.decompose(prior, current)
        expected = 2400.0 * math.log(1.1)
        self.assertAlmostEqual(e["total"], 0.0)
        self.assertAlmostEqual(e["visitors"], expected, places=6,
                               msg="flat revenue but visitors rose 10%%: the visitors effect should be about +%.1f, not 0" % expected)
        self.assertAlmostEqual(e["conversion"], -expected, places=6,
                               msg="flat revenue but conversion fell: the conversion effect should be about -%.1f" % expected)
        self.assertAlmostEqual(e["aov"], 0.0, places=9)

    def test_zero_factor_returns_none(self):
        prior = m.build_tree(500, 0, 0.0)   # a slice with no orders
        current = m.build_tree(520, 10, 600.0)
        e = m.decompose(prior, current)
        self.assertAlmostEqual(e["total"], 600.0, msg="total is still current revenue minus prior revenue")
        for f in FACTORS:
            self.assertIsNone(e[f], "a log of 0 is undefined: the %s effect should be None, not a number or an error" % f)
        self.assertIsNone(m.main_driver(e), "main_driver should return None when the effects are None")

    def test_main_driver_tie(self):
        e = {"visitors": 100.0, "conversion": -100.0, "aov": 5.0, "total": 5.0}
        self.assertEqual(m.main_driver(e), "visitors", "on a tie, return the factor listed first in FACTORS")
        e = {"visitors": 1.0, "conversion": 2.0, "aov": -3.0, "total": 0.0}
        self.assertEqual(m.main_driver(e), "aov", "compare absolute values: -3 is the largest effect")


class OnDataMixin:
    path = DATA

    def test_load_weeks(self):
        s = raw_sums(self.path)
        prior, current = m.load_weeks(self.path, SPLIT)
        self.assertEqual((prior["visitors"], prior["orders"]), (s["prior"][0], s["prior"][1]))
        self.assertEqual((current["visitors"], current["orders"]), (s["current"][0], s["current"][1]))
        self.assertAlmostEqual(prior["revenue"], s["prior"][2], places=2)
        self.assertAlmostEqual(current["conversion"], s["current"][1] / s["current"][0])

    def test_effects_sum_to_total(self):
        prior, current = m.load_weeks(self.path, SPLIT)
        e = m.decompose(prior, current)
        ref, total = reference_effects(raw_sums(self.path))
        self.assertAlmostEqual(e["total"], total, places=2)
        self.assertAlmostEqual(e["visitors"] + e["conversion"] + e["aov"], e["total"], places=6,
                               msg="the three effects must add up exactly to the revenue change")
        for f in FACTORS:
            self.assertAlmostEqual(e[f], ref[f], places=4, msg="%s effect: expected %.2f" % (f, ref[f]))

    def test_driver_and_channel(self):
        ref, _ = reference_effects(raw_sums(self.path))
        prior, current = m.load_weeks(self.path, SPLIT)
        self.assertEqual(m.main_driver(m.decompose(prior, current)), max(FACTORS, key=lambda f: abs(ref[f])))
        drops = {}
        for ch in CHANNELS:
            p, c = m.load_weeks(self.path, SPLIT, channel=ch)
            s = raw_sums(self.path, ch)
            self.assertEqual(p["visitors"], s["prior"][0], "channel filter: wrong prior visitors for %s" % ch)
            drops[ch] = m.decompose(p, c)["total"]
            self.assertAlmostEqual(drops[ch], s["current"][2] - s["prior"][2], places=2)
        self.assertEqual(min(drops, key=drops.get), "paid_social")


class TestOnData(OnDataMixin, unittest.TestCase):
    pass


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.path = os.path.join(cls.tmp, "daily_channels.csv")
        make_data.write_csv(make_data.build(seed=OTHER_SEED)["daily_channels"], cls.path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
