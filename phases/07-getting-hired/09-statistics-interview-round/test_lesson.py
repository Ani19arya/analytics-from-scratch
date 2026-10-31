"""Tests for lesson 07-09: the statistics interview round.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

Expected answers are computed below with statistics.NormalDist, separately from the lesson
code. Your functions run on the committed data, on data built in memory from other seeds,
and on small hand-made cases.
"""
import csv
import importlib.util
import math
import os
import sys
import unittest
from statistics import NormalDist

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)

sys.path.insert(0, HERE)
import make_data  # noqa: E402

N = NormalDist()


def read(name):
    with open(os.path.join(HERE, "data", name), newline="") as f:
        return list(csv.DictReader(f))


def seeded(seed):
    d = make_data.build(seed)
    exp = [dict(zip(make_data.EXPERIMENT_HEADER, [str(x) for x in r])) for r in d["experiment"]]
    cou = [dict(zip(make_data.COUPONS_HEADER, [str(x) for x in r])) for r in d["coupons"]]
    return exp, cou


def ref_z(x1, n1, x2, n2):
    p1, p2, pp = x1 / n1, x2 / n2, (x1 + x2) / (n1 + n2)
    se = (pp * (1 - pp) * (1 / n1 + 1 / n2)) ** 0.5
    if se == 0:
        return 100 * (p2 - p1), 0.0, 1.0
    z = (p2 - p1) / se
    return 100 * (p2 - p1), z, 2 * N.cdf(-abs(z))


def ref_power(p1, p2, n, alpha=0.05):
    pbar = (p1 + p2) / 2
    top = abs(p2 - p1) * n ** 0.5 - N.inv_cdf(1 - alpha / 2) * (2 * pbar * (1 - pbar)) ** 0.5
    return N.cdf(top / (p1 * (1 - p1) + p2 * (1 - p2)) ** 0.5)


def ref_n(p1, p2, power=0.8, alpha=0.05):
    pbar = (p1 + p2) / 2
    a = N.inv_cdf(1 - alpha / 2) * (2 * pbar * (1 - pbar)) ** 0.5
    b = N.inv_cdf(power) * (p1 * (1 - p1) + p2 * (1 - p2)) ** 0.5
    return math.ceil((a + b) ** 2 / (p2 - p1) ** 2)


def ref_table(rows):
    cells = {}
    for r in rows:
        for seg in (r["customer_type"], "all"):
            c = cells.setdefault((seg, r["coupon"]), [0, 0])
            c[0] += int(r["reordered"])
            c[1] += 1
    return cells


def ref_reversal(rows):
    cells = ref_table(rows)
    gap = {}
    for seg in {s for s, _ in cells}:
        if (seg, "yes") in cells and (seg, "no") in cells:
            gap[seg] = cells[(seg, "yes")][0] / cells[(seg, "yes")][1] - cells[(seg, "no")][0] / cells[(seg, "no")][1]
        else:
            gap[seg] = 0
    pooled = gap.pop("all")
    return pooled != 0 and all(g != 0 and (g > 0) != (pooled > 0) for g in gap.values())


def row(seg, coupon, reordered):
    return {"customer_type": seg, "coupon": coupon, "reordered": str(reordered)}


def kidney(seg, coupon, x, n):
    return [row(seg, coupon, 1)] * x + [row(seg, coupon, 0)] * (n - x)


class TestZTest(unittest.TestCase):
    def check(self, args, where):
        got = lesson.two_proportion_z(*args)
        want = ref_z(*args)
        for g, w, name in zip(got, want, ("difference in points", "z", "p-value")):
            self.assertAlmostEqual(g, w, places=6, msg="%s: wrong %s (pooled standard error, two-sided p)" % (where, name))

    def test_hand_made(self):
        self.check((100, 1000, 130, 1000), "10% vs 13% on 1,000 each")
        self.check((130, 1000, 100, 1000), "group 2 below group 1: the difference and z are negative")

    def test_no_gap_and_edges(self):
        self.assertEqual(lesson.two_proportion_z(0, 50, 0, 60), (0.0, 0.0, 1.0), "nobody converted: no gap, z 0, p 1")
        self.assertEqual(lesson.two_proportion_z(50, 50, 60, 60), (0.0, 0.0, 1.0), "everybody converted: no gap, z 0, p 1")
        d, z, p = lesson.two_proportion_z(10, 100, 10, 100)
        self.assertAlmostEqual(p, 1.0, places=9, msg="equal rates give p = 1")
        with self.assertRaises(ValueError, msg="a group with 0 users should raise ValueError"):
            lesson.two_proportion_z(0, 0, 5, 10)

    def test_committed_and_other_seeds(self):
        for where, rows in (("committed data", read("experiment.csv")),) + tuple(("seed %d" % s, seeded(s)[0]) for s in (5, 0, 21)):
            g = lesson.conversions(rows)
            (xc, nc), (xt, nt) = g["control"], g["treatment"]
            self.assertEqual(nc + nt, len(rows), "%s: every user is in one group" % where)
            self.check((xc, nc, xt, nt), where)


class TestPower(unittest.TestCase):
    def test_against_reference(self):
        for p1, p2, n in ((0.10, 0.115, 800), (0.10, 0.12, 3000), (0.30, 0.25, 500), (0.05, 0.06, 10000)):
            self.assertAlmostEqual(lesson.power(p1, p2, n), ref_power(p1, p2, n), places=6,
                                   msg="power(%s, %s, %d) is wrong: check z for 1 - alpha/2 and the two standard deviations" % (p1, p2, n))
        self.assertAlmostEqual(lesson.power(0.10, 0.12, 3000, alpha=0.01), ref_power(0.10, 0.12, 3000, alpha=0.01), places=6,
                               msg="use alpha: a stricter alpha lowers power")

    def test_n_per_group(self):
        for p1, p2 in ((0.10, 0.115), (0.20, 0.22), (0.50, 0.45)):
            n = lesson.n_per_group(p1, p2)
            self.assertEqual(n, ref_n(p1, p2), "n_per_group(%s, %s) is wrong: round up the formula from lesson 02-04" % (p1, p2))
            self.assertGreaterEqual(ref_power(p1, p2, n), 0.8 - 1e-9, "n_per_group should reach 80% power")
            self.assertLess(ref_power(p1, p2, n - 1), 0.8, "n_per_group should be the smallest n that reaches 80% power")
        self.assertEqual(lesson.n_per_group(0.10, 0.12, target_power=0.9), ref_n(0.10, 0.12, power=0.9), "use target_power")

    def test_no_gap(self):
        with self.assertRaises(ValueError, msg="power with p1 == p2 has no lift to find: raise ValueError"):
            lesson.power(0.1, 0.1, 100)
        with self.assertRaises(ValueError, msg="n_per_group with p1 == p2: raise ValueError"):
            lesson.n_per_group(0.1, 0.1)

    def test_bigger_n_more_power(self):
        self.assertLess(lesson.power(0.10, 0.115, 800), lesson.power(0.10, 0.115, 8000), "more users, more power")
        self.assertGreater(lesson.power(0.10, 0.115, 10 ** 7), 0.999, "with millions of users, power is almost 1")


class TestSimpson(unittest.TestCase):
    def test_classic_reversal(self):
        rows = kidney("small", "yes", 81, 87) + kidney("small", "no", 234, 270) + \
            kidney("large", "yes", 192, 263) + kidney("large", "no", 55, 80)
        t = lesson.rates_by_segment(rows, "customer_type", "coupon", "reordered")
        self.assertEqual(t["small"]["yes"][:2], (81, 87), "successes and count for one cell")
        self.assertEqual(t["all"]["yes"][:2], (273, 350), "'all' adds every segment together")
        self.assertAlmostEqual(t["all"]["no"][2], 289 / 350, places=9)
        self.assertTrue(lesson.simpson_reversal(t, "no", "yes"),
                        "yes is better in each segment but worse in 'all': that is a reversal")
        self.assertTrue(lesson.simpson_reversal(t, "yes", "no"), "swapping a and b flips every sign, so it is still a reversal")

    def test_no_reversal(self):
        rows = kidney("small", "yes", 8, 10) + kidney("small", "no", 6, 10) + \
            kidney("large", "yes", 5, 10) + kidney("large", "no", 3, 10)
        t = lesson.rates_by_segment(rows, "customer_type", "coupon", "reordered")
        self.assertFalse(lesson.simpson_reversal(t, "no", "yes"), "the same direction everywhere is not a reversal")

    def test_tie_and_missing(self):
        rows = kidney("small", "yes", 9, 10) + kidney("small", "no", 9, 10) + \
            kidney("large", "yes", 1, 10) + kidney("large", "no", 7, 30)
        t = lesson.rates_by_segment(rows, "customer_type", "coupon", "reordered")
        self.assertFalse(lesson.simpson_reversal(t, "no", "yes"), "a segment with a gap of exactly 0 does not reverse")
        rows = kidney("small", "yes", 3, 10) + kidney("small", "no", 1, 10) + kidney("large", "yes", 2, 10)
        t = lesson.rates_by_segment(rows, "customer_type", "coupon", "reordered")
        self.assertNotIn("no", t["large"], "a group with no rows in a segment has no cell")
        self.assertFalse(lesson.simpson_reversal(t, "no", "yes"), "a segment missing one group cannot reverse")
        self.assertEqual(lesson.rates_by_segment([], "customer_type", "coupon", "reordered"), {}, "no rows, empty table")
        self.assertFalse(lesson.simpson_reversal({}, "no", "yes"), "an empty table is not a reversal")

    def test_committed_and_other_seeds(self):
        seen = set()
        for where, rows in (("committed data", read("coupons.csv")),) + tuple(("seed %d" % s, seeded(s)[1]) for s in (0, 3, 15, 13)):
            t = lesson.rates_by_segment(rows, "customer_type", "coupon", "reordered")
            for (seg, coupon), (x, n) in ref_table(rows).items():
                self.assertEqual(t[seg][coupon][:2], (x, n), "%s: wrong count for %s, coupon %s" % (where, seg, coupon))
            want = ref_reversal(rows)
            self.assertEqual(lesson.simpson_reversal(t, "no", "yes"), want, "%s: reversal should be %s" % (where, want))
            seen.add(want)
        self.assertEqual(seen, {True, False}, "the seeds should include tables that reverse and tables that do not")


class TestVerdicts(unittest.TestCase):
    def test_statements(self):
        truth = {1: False, 2: True, 3: False, 4: True, 5: False, 6: True, 7: False, 8: False}
        self.assertEqual(sorted(lesson.VERDICTS), sorted(truth), "give a True or False verdict for each of the 8 statements")
        wrong = [k for k in sorted(truth) if lesson.VERDICTS[k] is not truth[k]]
        self.assertEqual(wrong, [], "these verdicts are wrong: %s. Re-read The idea, then try again" % wrong)


if __name__ == "__main__":
    unittest.main()
