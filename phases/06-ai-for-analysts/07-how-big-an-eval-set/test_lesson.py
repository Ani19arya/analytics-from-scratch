"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py.

Expected answers are worked out here a second way: the Wilson interval from its closed
form, the paired interval from the mean and variance of per-ticket differences, and the
sample sizes by checking the power (or the margin) at n and at n - 1.
"""
import csv
import importlib.util
import json
import math
import os
import unittest
from statistics import NormalDist

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lesson = load("lesson", TARGET)
make_data = load("make_data", os.path.join(HERE, "make_data.py"))

OTHER_SEED = 1672
PHI = NormalDist().cdf


def committed_rows():
    with open(os.path.join(HERE, "data", "labelled_tickets.csv"), newline="") as f:
        return list(csv.DictReader(f))


def ref_wilson(k, n, z=1.96):
    """(2np + z^2 +/- z*sqrt(z^2 + 4np(1-p))) / (2(n + z^2)), the same interval written another way."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    root = z * math.sqrt(z * z + 4 * n * p * (1 - p))
    return (2 * n * p + z * z - root) / (2 * (n + z * z)), (2 * n * p + z * z + root) / (2 * (n + z * z))


def ref_half(p, n):
    low, high = ref_wilson(p * n, n)
    return (high - low) / 2


def ref_paired(rows, a="v2", b="v3"):
    """Per-ticket difference d = (b right) - (a right). Interval: mean(d) +/- 1.96 * sd(d) / sqrt(n)."""
    n = len(rows)
    if n == 0:
        return -1.0, 1.0
    d = [int(r[b + "_label"] == r["gold_label"]) - int(r[a + "_label"] == r["gold_label"]) for r in rows]
    mean = sum(d) / n
    var = sum((x - mean) ** 2 for x in d) / n
    se = math.sqrt(var / n)
    return mean - 1.96 * se, mean + 1.96 * se


def ref_verdict(rows):
    low, high = ref_paired(rows)
    if low > 0:
        return "v3 better"
    if high < 0:
        return "v2 better"
    return "not proven"


def rows_from_table(both, only_a, only_b, neither):
    """Hand-made tickets: label 'x' is the truth; 'y' is wrong."""
    cells = [(both, "x", "x"), (only_a, "x", "y"), (only_b, "y", "x"), (neither, "y", "y")]
    out = []
    for count, v2, v3 in cells:
        for _ in range(count):
            out.append({"gold_label": "x", "v2_label": v2, "v3_label": v3})
    return out


class TestOneScore(unittest.TestCase):
    def test_wilson_matches_closed_form(self):
        for k, n in [(44, 50), (87, 100), (0, 10), (10, 10), (1, 2), (1391, 1600), (0, 0)]:
            low, high = lesson.wilson_interval(k, n)
            exp_low, exp_high = ref_wilson(k, n)
            self.assertAlmostEqual(low, exp_low, places=9, msg="Wilson low for %d/%d: check the formula" % (k, n))
            self.assertAlmostEqual(high, exp_high, places=9, msg="Wilson high for %d/%d: check the formula" % (k, n))

    def test_margin_is_half_width(self):
        self.assertAlmostEqual(lesson.margin(0, 0), 0.5, msg="with no tickets the interval is 0 to 1, so the margin is 0.5")
        low, high = ref_wilson(44, 50)
        self.assertAlmostEqual(lesson.margin(44, 50), (high - low) / 2)

    def test_quadruple_n_roughly_halves_margin(self):
        m1 = lesson.margin(87, 100)
        m4 = lesson.margin(348, 400)
        self.assertAlmostEqual(m1 / m4, 2.0, delta=0.1, msg="four times the tickets should give about half the margin")

    def test_n_for_margin_is_the_smallest_n(self):
        for p, target in [(0.87, 0.02), (0.87, 0.05), (0.5, 0.03), (0.99, 0.01), (0.5, 0.49)]:
            n = lesson.n_for_margin(p, target)
            self.assertLessEqual(ref_half(p, n), target, "n = %d for p=%.2f still has a margin above %.2f" % (n, p, target))
            if n > 1:
                self.assertGreater(ref_half(p, n - 1), target,
                                   "n = %d is not the smallest: %d already gives a margin of %.2f at p=%.2f" % (n, n - 1, target, p))

    def test_n_for_margin_rejects_bad_targets(self):
        for target in [0, -0.1, 0.5, 1]:
            with self.assertRaises(ValueError, msg="a target margin of %s makes no sense and should raise ValueError" % target):
                lesson.n_for_margin(0.87, target)


class TestComparison(unittest.TestCase):
    def test_paired_table_small_and_empty(self):
        self.assertEqual(lesson.paired_table([]), (0, 0, 0, 0))
        self.assertEqual(lesson.paired_table(rows_from_table(3, 1, 2, 4)), (3, 1, 2, 4))

    def test_paired_interval_matches_per_ticket_differences(self):
        for table in [(41, 2, 3, 4), (84, 5, 5, 6), (0, 0, 7, 0), (10, 0, 0, 0), (1291, 91, 109, 109)]:
            rows = rows_from_table(*table)
            low, high = lesson.paired_difference_interval(table[1], table[2], len(rows))
            exp_low, exp_high = ref_paired(rows)
            self.assertAlmostEqual(low, exp_low, places=9, msg="paired interval low for table %s" % (table,))
            self.assertAlmostEqual(high, exp_high, places=9, msg="paired interval high for table %s" % (table,))
        self.assertEqual(lesson.paired_difference_interval(0, 0, 0), (-1.0, 1.0), "with no tickets there is no evidence: (-1.0, 1.0)")

    def test_verdict_three_outcomes(self):
        self.assertEqual(lesson.verdict(rows_from_table(800, 10, 60, 130)), "v3 better")
        self.assertEqual(lesson.verdict(rows_from_table(800, 60, 10, 130)), "v2 better")
        self.assertEqual(lesson.verdict(rows_from_table(41, 2, 3, 4)), "not proven",
                         "3 against 2 discordant tickets cannot prove anything")
        self.assertEqual(lesson.verdict(rows_from_table(10, 0, 0, 0)), "not proven",
                         "when both versions agree on every ticket there is no difference to prove")
        self.assertEqual(lesson.verdict([]), "not proven")

    def test_committed_prefixes(self):
        rows = committed_rows()
        for n in [50, 100, 200, 400, 800, 1600]:
            part = rows[:n]
            v2 = sum(1 for r in part if r["v2_label"] == r["gold_label"])
            v3 = sum(1 for r in part if r["v3_label"] == r["gold_label"])
            both = sum(1 for r in part if r["v2_label"] == r["gold_label"] and r["v3_label"] == r["gold_label"])
            table = lesson.paired_table(part)
            self.assertEqual(table[0], both, "first %d tickets: both-right count" % n)
            self.assertEqual(table[0] + table[1], v2, "first %d tickets: v2 right count" % n)
            self.assertEqual(table[0] + table[2], v3, "first %d tickets: v3 right count" % n)
            self.assertEqual(sum(table), n)
            self.assertEqual(lesson.verdict(part), ref_verdict(part), "first %d tickets: verdict differs from the reference" % n)
        self.assertEqual(lesson.verdict(rows), "not proven",
                         "even 1,600 tickets cannot prove a 2-point gain here: the interval still includes 0")

    def test_second_dataset(self):
        rows = make_data.build(seed=OTHER_SEED)["tickets"]
        for n in [50, 200, 800, len(rows)]:
            part = rows[:n]
            table = lesson.paired_table(part)
            only_v2 = sum(1 for r in part if r["v2_label"] == r["gold_label"] and r["v3_label"] != r["gold_label"])
            only_v3 = sum(1 for r in part if r["v3_label"] == r["gold_label"] and r["v2_label"] != r["gold_label"])
            self.assertEqual((table[1], table[2]), (only_v2, only_v3), "seed %d, first %d: discordant counts" % (OTHER_SEED, n))
            self.assertEqual(lesson.verdict(part), ref_verdict(part), "seed %d, first %d: verdict" % (OTHER_SEED, n))


class TestSampleSize(unittest.TestCase):
    def paired_power(self, n, delta, psi):
        return PHI((delta * math.sqrt(n) - 1.96 * math.sqrt(psi)) / math.sqrt(psi - delta * delta))

    def unpaired_power(self, n, p1, p2):
        return PHI(abs(p1 - p2) * math.sqrt(n) / math.sqrt(p1 * (1 - p1) + p2 * (1 - p2)) - 1.96)

    def test_paired_n_is_smallest_with_80_percent_power(self):
        for delta, psi in [(0.02, 0.12), (0.05, 0.12), (0.10, 0.20), (0.03, 0.03)]:
            n = lesson.n_for_paired_difference(delta, psi)
            self.assertIsInstance(n, int, "round the ticket count up to a whole number")
            self.assertGreaterEqual(self.paired_power(n, delta, psi), 0.8 - 1e-4,
                                    "n = %d gives less than 80%% power for a gain of %.2f" % (n, delta))
            self.assertLess(self.paired_power(n - 1, delta, psi), 0.8 + 1e-4,
                            "n = %d is not the smallest: n - 1 already has 80%% power" % n)

    def test_unpaired_n_is_smallest_with_80_percent_power(self):
        for p1, p2 in [(0.86, 0.88), (0.80, 0.90), (0.5, 0.6)]:
            n = lesson.n_for_unpaired_difference(p1, p2)
            self.assertIsInstance(n, int, "round the ticket count up to a whole number")
            self.assertGreaterEqual(self.unpaired_power(n, p1, p2), 0.8 - 1e-4)
            self.assertLess(self.unpaired_power(n - 1, p1, p2), 0.8 + 1e-4)

    def test_pairing_needs_fewer_tickets(self):
        paired = lesson.n_for_paired_difference(0.02, 0.12)
        unpaired = lesson.n_for_unpaired_difference(0.86, 0.88)
        self.assertLess(paired, unpaired, "grading both versions on the same tickets should need fewer tickets per version")

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            lesson.n_for_paired_difference(0, 0.12)
        with self.assertRaises(ValueError, msg="a gain bigger than the discordant share is impossible"):
            lesson.n_for_paired_difference(0.2, 0.1)
        with self.assertRaises(ValueError):
            lesson.n_for_unpaired_difference(0.86, 0.86)


class TestFixture(unittest.TestCase):
    def test_fixture_is_labelled_simulated(self):
        with open(os.path.join(HERE, "data", "fixture.json")) as f:
            info = json.load(f)
        self.assertEqual(info["label_source"], "simulated")
        self.assertTrue(info["model"].startswith("none"))
        self.assertEqual(committed_rows(), make_data.build()["tickets"], "data/labelled_tickets.csv is out of date: run make_data.py")


if __name__ == "__main__":
    unittest.main()
