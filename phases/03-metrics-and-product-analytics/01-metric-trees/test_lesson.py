"""Tests for lesson 01: metric trees. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead."""
import csv
import importlib.util
import math
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "daily_channels.csv")
SPLIT = "2026-10-12"
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


def raw_sums(channel=None):
    sums = {"prior": [0, 0, 0.0], "current": [0, 0, 0.0]}
    with open(DATA, newline="") as f:
        for row in csv.DictReader(f):
            if channel and row["channel"] != channel:
                continue
            k = "prior" if row["date"] < SPLIT else "current"
            sums[k][0] += int(row["visitors"])
            sums[k][1] += int(row["orders"])
            sums[k][2] += float(row["revenue"])
    return sums


class TestTree(unittest.TestCase):
    def test_build_tree(self):
        t = m.build_tree(1000, 40, 2400.0)
        self.assertAlmostEqual(t["conversion"], 0.04)
        self.assertAlmostEqual(t["aov"], 60.0)
        self.assertAlmostEqual(t["visitors"] * t["conversion"] * t["aov"], t["revenue"])

    def test_zero_orders(self):
        t = m.build_tree(500, 0, 0.0)
        self.assertEqual(t["aov"], 0.0)
        self.assertEqual(t["conversion"], 0.0)

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


class TestOnData(unittest.TestCase):
    def test_load_weeks(self):
        s = raw_sums()
        prior, current = m.load_weeks(DATA, SPLIT)
        self.assertEqual((prior["visitors"], prior["orders"]), (s["prior"][0], s["prior"][1]))
        self.assertEqual((current["visitors"], current["orders"]), (s["current"][0], s["current"][1]))
        self.assertAlmostEqual(prior["revenue"], s["prior"][2], places=2)
        self.assertAlmostEqual(current["conversion"], s["current"][1] / s["current"][0])

    def test_effects_sum_to_total(self):
        prior, current = m.load_weeks(DATA, SPLIT)
        e = m.decompose(prior, current)
        self.assertAlmostEqual(e["total"], current["revenue"] - prior["revenue"], places=2)
        self.assertAlmostEqual(e["visitors"] + e["conversion"] + e["aov"], e["total"], places=6)
        ref = e["total"] * math.log(current["conversion"] / prior["conversion"]) / math.log(current["revenue"] / prior["revenue"])
        self.assertAlmostEqual(e["conversion"], ref, places=6)

    def test_driver_and_channel(self):
        prior, current = m.load_weeks(DATA, SPLIT)
        self.assertEqual(m.main_driver(m.decompose(prior, current)), "conversion")
        p, c = m.load_weeks(DATA, SPLIT, channel="paid_social")
        s = raw_sums("paid_social")
        self.assertEqual(p["visitors"], s["prior"][0])
        drops = {}
        for ch in ("search", "email", "paid_social"):
            p, c = m.load_weeks(DATA, SPLIT, channel=ch)
            drops[ch] = m.decompose(p, c)["total"]
        self.assertEqual(min(drops, key=drops.get), "paid_social")


if __name__ == "__main__":
    unittest.main()
