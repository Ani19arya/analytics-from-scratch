"""Tests for lesson 09: segmentation and mix effects. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Every expected number is computed here in plain Python, never read from the solution.
The tests run on the committed data and on a second dataset built with another seed."""
import csv
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "daily_devices.csv")
SPLIT = "2026-10-01"
OTHER_SEED = 4
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


def sums(path):
    out = {"prior": {}, "current": {}}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            k = "prior" if r["date"] < SPLIT else "current"
            a = out[k].setdefault(r["device"], [0, 0])
            a[0] += int(r["sessions"])
            a[1] += int(r["orders"])
    return out


def shapley(prior, current):
    """A second route to the totals: the two-factor Shapley split, which averages
    'change the mix first' and 'change the rates first'."""
    segs = sorted(set(prior) | set(current))
    n0 = sum(v[0] for v in prior.values())
    n1 = sum(v[0] for v in current.values())
    w0 = {s: prior.get(s, [0, 0])[0] / n0 for s in segs}
    w1 = {s: current.get(s, [0, 0])[0] / n1 for s in segs}
    r0, r1 = {}, {}
    for s in segs:
        a, b = prior.get(s, [0, 0]), current.get(s, [0, 0])
        r0[s] = a[1] / a[0] if a[0] else b[1] / b[0]
        r1[s] = b[1] / b[0] if b[0] else r0[s]

    def total(w, r):
        return sum(w[s] * r[s] for s in segs)

    mix = 0.5 * ((total(w1, r0) - total(w0, r0)) + (total(w1, r1) - total(w0, r1)))
    rate = 0.5 * ((total(w0, r1) - total(w0, r0)) + (total(w1, r1) - total(w1, r0)))
    return mix, rate, total(w1, r1) - total(w0, r0)


class TestSmallCases(unittest.TestCase):
    def test_identical_periods(self):
        p = {"a": [100, 5], "b": [50, 1]}
        r = m.decompose(p, {k: list(v) for k, v in p.items()})
        self.assertEqual((round(r["total"], 12), round(r["mix"], 12), round(r["rate"], 12)), (0.0, 0.0, 0.0))

    def test_pure_mix(self):
        # every segment keeps its rate, only the shares move
        r = m.decompose({"desk": [100, 4], "mob": [100, 1]}, {"desk": [100, 4], "mob": [300, 3]})
        self.assertAlmostEqual(r["rate"], 0.0, places=12, msg="no segment rate changed, so the rate effect must be 0")
        self.assertAlmostEqual(r["mix"], r["total"], places=12)
        self.assertLess(r["segments"]["mob"]["mix"], 0,
                        "mobile grew and converts below average, so its mix effect is negative")

    def test_pure_rate(self):
        r = m.decompose({"a": [100, 4], "b": [100, 1]}, {"a": [100, 6], "b": [100, 1]})
        self.assertAlmostEqual(r["mix"], 0.0, places=12, msg="the shares did not move, so the mix effect must be 0")
        self.assertAlmostEqual(r["rate"], 0.01, places=12)

    def test_new_segment(self):
        r = m.decompose({"a": [100, 2]}, {"a": [100, 2], "app": [100, 8]})
        self.assertAlmostEqual(r["segments"]["app"]["rate"], 0.0, places=12,
                               msg="a segment with no prior sessions has no rate change: all of it is mix")
        self.assertAlmostEqual(r["mix"] + r["rate"], r["total"], places=12)
        self.assertAlmostEqual(r["total"], 0.03, places=12)

    def test_empty_and_zero(self):
        self.assertIsNone(m.overall_rate({}), "no sessions: the rate is None, not 0 or an error")
        self.assertIsNone(m.decompose({}, {"a": [10, 1]}), "decompose returns None when a period has no sessions")
        self.assertEqual(m.overall_rate({"a": [10, 0]}), 0.0, "zero orders is a real 0 rate")
        r = m.decompose({"a": [10, 1], "gone": [0, 0]}, {"a": [10, 2], "gone": [0, 0]})
        self.assertNotIn("gone", r["segments"], "a segment with no sessions in either period is skipped")

    def test_main_cause(self):
        self.assertEqual(m.main_cause({"mix": -0.3, "rate": 0.1}), "mix", "compare absolute sizes")
        self.assertEqual(m.main_cause({"mix": 0.1, "rate": -0.1}), "rate", "a tie goes to rate")


class OnDataMixin:
    path = DATA

    def test_load(self):
        self.assertEqual(m.load_periods(self.path, SPLIT), sums(self.path))

    def test_decompose_matches_shapley(self):
        s = sums(self.path)
        r = m.decompose(s["prior"], s["current"])
        mix, rate, total = shapley(s["prior"], s["current"])
        self.assertAlmostEqual(r["total"], total, places=12)
        self.assertAlmostEqual(r["mix"], mix, places=12, msg="mix effect: expected %.5f points" % (100 * mix))
        self.assertAlmostEqual(r["rate"], rate, places=12, msg="rate effect: expected %.5f points" % (100 * rate))
        self.assertAlmostEqual(r["mix"] + r["rate"], r["total"], places=12,
                               msg="mix + rate must add up exactly to the total change")

    def test_segment_effects(self):
        s = sums(self.path)
        r = m.decompose(s["prior"], s["current"])
        n0 = sum(v[0] for v in s["prior"].values())
        n1 = sum(v[0] for v in s["current"].values())
        R0 = sum(v[1] for v in s["prior"].values()) / n0
        R1 = sum(v[1] for v in s["current"].values()) / n1
        for seg in s["prior"]:
            (a0, b0), (a1, b1) = s["prior"][seg], s["current"][seg]
            w0, w1, r0, r1 = a0 / n0, a1 / n1, b0 / a0, b1 / a1
            got = r["segments"][seg]
            self.assertAlmostEqual(got["rate"], (r1 - r0) * (w0 + w1) / 2, places=12)
            self.assertAlmostEqual(got["mix"], (w1 - w0) * ((r0 + r1) / 2 - (R0 + R1) / 2), places=12,
                                   msg="%s mix: measure the segment's rate against the average overall rate" % seg)
        self.assertAlmostEqual(sum(c["mix"] for c in r["segments"].values()), r["mix"], places=12)

    def test_main_cause_on_data(self):
        s = sums(self.path)
        mix, rate, _ = shapley(s["prior"], s["current"])
        self.assertEqual(m.main_cause(m.decompose(s["prior"], s["current"])), "mix" if abs(mix) > abs(rate) else "rate")


class TestOnData(OnDataMixin, unittest.TestCase):
    pass


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.path = os.path.join(cls.tmp, "daily_devices.csv")
        make_data.write_csv(make_data.build(seed=OTHER_SEED)["daily_devices"], cls.path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
