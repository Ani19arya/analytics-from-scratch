"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py.

Expected answers are worked out here a second way: the precision at every threshold by
sorting tickets from most to least confident and keeping running totals, and the Wilson
interval from its closed form.
"""
import csv
import importlib.util
import json
import math
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lesson = load("lesson", TARGET)
make_data = load("make_data", os.path.join(HERE, "make_data.py"))

OTHER_SEED = 1612


def as_rows(rows):
    return [dict(r, confidence=float(r["confidence"])) for r in rows]


def committed(split):
    with open(os.path.join(HERE, "data", "tickets.csv"), newline="") as f:
        return as_rows([r for r in csv.DictReader(f) if r["split"] == split])


def ref_wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 1.0
    p = k / n
    root = z * math.sqrt(z * z + 4 * n * p * (1 - p))
    return (2 * n * p + z * z - root) / (2 * (n + z * z)), (2 * n * p + z * z + root) / (2 * (n + z * z))


def ref_curve(rows):
    """{threshold: (auto, right)} for every distinct confidence, from running totals."""
    ordered = sorted(rows, key=lambda r: -r["confidence"])
    curve = {}
    auto = right = 0
    for i, r in enumerate(ordered):
        auto += 1
        right += r["llm_label"] == r["gold_label"]
        if i + 1 == len(ordered) or ordered[i + 1]["confidence"] != r["confidence"]:
            curve[r["confidence"]] = (auto, right)
    return curve


def ref_choose(rows, target=0.95, min_auto=50):
    curve = ref_curve(rows)
    ok = [t for t, (auto, right) in curve.items() if auto >= min_auto and right / auto >= target]
    return min(ok) if ok else None


def ticket(conf, right=True, label="bug"):
    return {"confidence": conf, "gold_label": label, "llm_label": label if right else "other"}


class TestSmallCases(unittest.TestCase):
    def test_at_threshold_counts_ties_as_auto(self):
        rows = [ticket(0.9), ticket(0.9, False), ticket(0.8), ticket(0.95)]
        self.assertEqual(lesson.at_threshold(rows, 0.9), (3, 2, 2 / 3, 0.75),
                         "a ticket whose confidence equals the threshold is auto-handled (>=)")

    def test_empty_and_nothing_auto(self):
        self.assertEqual(lesson.at_threshold([], 0.9), (0, 0, 0.0, 0.0), "no rows: return zeros, not a crash")
        self.assertEqual(lesson.at_threshold([ticket(0.5)], 0.9), (0, 0, 0.0, 0.0))
        self.assertIsNone(lesson.choose_threshold([]), "no tickets: no threshold can be chosen")

    def test_choose_takes_lowest_qualifying(self):
        # 60 sure tickets at 0.99 all right, 40 at 0.80 of which 30 right
        rows = [ticket(0.99) for _ in range(60)] + [ticket(0.80, i < 30) for i in range(40)]
        self.assertEqual(lesson.choose_threshold(rows, 0.95, 50), 0.99)
        self.assertEqual(lesson.choose_threshold(rows, 0.90, 50), 0.80,
                         "at 0.80 precision is 90/100: the lowest threshold that meets 0.90 must win")
        self.assertIsNone(lesson.choose_threshold(rows, 0.95, 61),
                          "only 60 tickets clear 0.95, so with min_auto 61 nothing qualifies")

    def test_precision_not_monotonic(self):
        # top 50 at 0.99 have 2 wrong (0.96); adding 50 perfect ones at 0.90 lifts it to 0.98
        rows = [ticket(0.99, i >= 2) for i in range(50)] + [ticket(0.90) for _ in range(50)]
        self.assertEqual(lesson.choose_threshold(rows, 0.97, 50), 0.90,
                         "precision can rise as the threshold drops: check every threshold, do not stop at the first failure")

    def test_report_keys_and_interval(self):
        rows = [ticket(0.99) for _ in range(19)] + [ticket(0.99, False), ticket(0.5)]
        rep = lesson.report(rows, 0.9)
        low, high = ref_wilson(19, 20)
        self.assertEqual(rep["auto"], 20)
        self.assertEqual(rep["right"], 19)
        self.assertEqual(rep["to_review"], 1)
        self.assertAlmostEqual(rep["precision"], 0.95, places=3)
        self.assertAlmostEqual(rep["low"], round(low, 3), places=3, msg="low is the Wilson lower bound for right out of auto")
        self.assertAlmostEqual(rep["high"], round(high, 3), places=3)
        self.assertAlmostEqual(rep["coverage"], round(20 / 21, 3), places=3)

    def test_calibration_bins(self):
        rows = [ticket(0.6), ticket(0.65, False), ticket(1.0), ticket(0.9, False)]
        cal = lesson.calibration(rows, [0.5, 0.7, 0.9, 1.0])
        self.assertEqual(cal[0][:3], (0.5, 0.7, 2))
        self.assertAlmostEqual(cal[0][3], 0.625, places=3)
        self.assertAlmostEqual(cal[0][4], 0.5, places=3)
        self.assertEqual(cal[1], (0.7, 0.9, 0, None, None), "an empty bin gives None for the means")
        self.assertEqual(cal[2][2], 2, "the last bin includes its top edge, so confidence 1.0 counts")

    def test_review_queue_and_hours(self):
        rows = [ticket(0.5, label="bug"), ticket(0.6, label="refund"), ticket(0.7, label="refund"), ticket(0.95)]
        self.assertEqual(lesson.review_queue(rows, 0.9), {"refund": 2, "bug": 1},
                         "count the tickets below the threshold by the label the LLM gave")
        self.assertEqual(lesson.review_hours(0.6, weekly=1000, minutes=3), 20.0)
        self.assertEqual(lesson.review_hours(1.0, weekly=1000, minutes=3), 0.0)


class TestData(unittest.TestCase):
    def check_split(self, val, held, label):
        t = lesson.choose_threshold(val)
        self.assertEqual(t, ref_choose(val), "%s: the chosen threshold differs from the reference" % label)
        curve = ref_curve(held)
        auto = sum(1 for r in held if r["confidence"] >= t)
        right = sum(1 for r in held if r["confidence"] >= t and r["llm_label"] == r["gold_label"])
        rep = lesson.report(held, t)
        self.assertEqual((rep["auto"], rep["right"]), (auto, right), "%s: held-out counts at the chosen threshold" % label)
        self.assertEqual(rep["to_review"], len(held) - auto)
        low, _ = ref_wilson(right, auto)
        self.assertAlmostEqual(rep["low"], round(low, 3), places=3)
        for th, (a, rt) in list(curve.items())[:20]:
            got = lesson.at_threshold(held, th)
            self.assertEqual(got[:2], (a, rt), "%s: counts at threshold %.2f" % (label, th))
        queue = lesson.review_queue(held, t)
        self.assertEqual(sum(queue.values()), len(held) - auto)
        return t, rep

    def test_committed(self):
        t, rep = self.check_split(committed("validation"), committed("heldout"), "committed data")
        self.assertEqual(t, 0.91)
        self.assertLess(rep["precision"], lesson.report(committed("validation"), t)["precision"],
                        "held-out precision is lower than validation precision here: report the held-out number")

    def test_second_dataset(self):
        rows = as_rows(make_data.build(seed=OTHER_SEED)["tickets"])
        val = [r for r in rows if r["split"] == "validation"]
        held = [r for r in rows if r["split"] == "heldout"]
        self.check_split(val, held, "seed %d" % OTHER_SEED)

    def test_fixture(self):
        with open(os.path.join(HERE, "data", "fixture.json")) as f:
            info = json.load(f)
        self.assertEqual(info["label_source"], "simulated")
        self.assertTrue(info["model"].startswith("none"))


if __name__ == "__main__":
    unittest.main()
