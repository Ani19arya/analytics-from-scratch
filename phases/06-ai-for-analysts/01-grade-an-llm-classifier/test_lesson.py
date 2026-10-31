"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py."""
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

LABELS = ["billing", "bug", "refund", "other"]
OTHER_SEED = 1601


def tiny_rows():
    pairs = [("a", "a"), ("a", "b"), ("b", "b"), ("b", "b"), ("b", "a")]
    return [{"human_label": h, "llm_label": p} for h, p in pairs]


def committed_rows():
    with open(os.path.join(HERE, "data", "tickets.csv"), newline="") as f:
        return list(csv.DictReader(f))


def ref_wilson(k, n, z=1.96):
    """Independent form of the Wilson interval: (2np + z^2 +/- z*sqrt(z^2 + 4np(1-p))) / (2(n + z^2))."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    root = z * math.sqrt(z * z + 4 * n * p * (1 - p))
    return (2 * n * p + z * z - root) / (2 * (n + z * z)), (2 * n * p + z * z + root) / (2 * (n + z * z))


def ref_decision(rows, label, min_p=0.90, min_r=0.80):
    tp = sum(1 for r in rows if r["human_label"] == label and r["llm_label"] == label)
    pred = sum(1 for r in rows if r["llm_label"] == label)
    act = sum(1 for r in rows if r["human_label"] == label)
    p_low, p_high = ref_wilson(tp, pred)
    r_low, r_high = ref_wilson(tp, act)
    if p_low >= min_p and r_low >= min_r:
        return "yes"
    if p_high < min_p or r_high < min_r:
        return "no"
    return "not proven"


def cm_from_cells(tp, fp, fn, tn):
    """A two-label matrix for label 'x': fp are 'y' tickets predicted 'x', fn are 'x' tickets predicted 'y'."""
    return {"x": {"x": tp, "y": fn}, "y": {"x": fp, "y": tn}}


class TestClassifierGrade(unittest.TestCase):
    def test_tiny_confusion_matrix(self):
        cm = lesson.confusion_matrix(tiny_rows(), ["a", "b"])
        self.assertEqual(cm, {"a": {"a": 1, "b": 1}, "b": {"a": 1, "b": 2}})

    def test_empty_rows_give_zero_matrix(self):
        cm = lesson.confusion_matrix([], ["a", "b"])
        self.assertEqual(cm, {"a": {"a": 0, "b": 0}, "b": {"a": 0, "b": 0}},
                         "every label must be a key even when there are no rows")
        self.assertEqual(lesson.accuracy(cm), 0.0, "accuracy of an empty matrix should be 0.0, not a crash")

    def test_tiny_metrics(self):
        cm = lesson.confusion_matrix(tiny_rows(), ["a", "b"])
        self.assertEqual(lesson.counts(cm, "b"), (2, 1, 1))
        p, r, f1 = lesson.precision_recall_f1(cm, "b")
        self.assertAlmostEqual(p, 2 / 3)
        self.assertAlmostEqual(r, 2 / 3)
        self.assertAlmostEqual(f1, 2 / 3)
        self.assertAlmostEqual(lesson.accuracy(cm), 3 / 5)

    def test_zero_division(self):
        cm = {"x": {"x": 0, "y": 3}, "y": {"x": 0, "y": 2}}
        self.assertEqual(lesson.precision_recall_f1(cm, "x"), (0.0, 0.0, 0.0))

    def test_full_data_matches_independent_count(self):
        rows = committed_rows()
        cm = lesson.confusion_matrix(rows, LABELS)
        self.assertEqual(sum(sum(r.values()) for r in cm.values()), len(rows))
        for label in LABELS:
            tp = sum(1 for r in rows if r["human_label"] == label and r["llm_label"] == label)
            pred = sum(1 for r in rows if r["llm_label"] == label)
            act = sum(1 for r in rows if r["human_label"] == label)
            p, r, f1 = lesson.precision_recall_f1(cm, label)
            self.assertAlmostEqual(p, tp / pred)
            self.assertAlmostEqual(r, tp / act)
            self.assertAlmostEqual(f1, 2 * tp / (pred + act))

    def test_wilson_matches_independent_formula(self):
        for k, n in [(63, 76), (63, 77), (1, 2), (45, 50), (0, 10), (10, 10), (0, 0)]:
            low, high = lesson.wilson_interval(k, n)
            exp_low, exp_high = ref_wilson(k, n)
            self.assertAlmostEqual(low, exp_low, places=9, msg="Wilson low for %d/%d: check the formula" % (k, n))
            self.assertAlmostEqual(high, exp_high, places=9, msg="Wilson high for %d/%d: check the formula" % (k, n))

    def test_wilson_edges(self):
        self.assertEqual(lesson.wilson_interval(0, 0), (0.0, 1.0), "with n = 0 the interval should be (0.0, 1.0)")
        low, high = lesson.wilson_interval(0, 10)
        self.assertAlmostEqual(low, 0.0, places=12, msg="0 out of 10 should have a lower bound of 0")
        self.assertGreater(high, 0.2, "0 out of 10 still allows a true rate above 20%")
        low, high = lesson.wilson_interval(10, 10)
        self.assertAlmostEqual(high, 1.0, places=12)
        self.assertLess(low, 0.8, "10 out of 10 does not prove a rate above 80%")

    def test_rule(self):
        self.assertTrue(lesson.meets_rule(0.90, 0.80))
        self.assertFalse(lesson.meets_rule(0.95, 0.79))
        self.assertFalse(lesson.meets_rule(0.89, 0.99))

    def test_decide_three_outcomes(self):
        # 980 of 1000 right both ways: lower bounds clear 0.90 and 0.80
        self.assertEqual(lesson.decide(cm_from_cells(980, 20, 20, 500), "x"), "yes")
        # precision 50/100: even the upper bound is far below 0.90
        self.assertEqual(lesson.decide(cm_from_cells(50, 50, 5, 500), "x"), "no")
        # 19 of 20 right both ways: point values pass, the sample is too small to prove it
        self.assertEqual(lesson.decide(cm_from_cells(19, 1, 1, 50), "x"), "not proven",
                         "19/20 is 0.95 but its interval reaches below 0.90: that is 'not proven'")
        # nothing predicted at all: no evidence either way
        self.assertEqual(lesson.decide(cm_from_cells(0, 0, 0, 10), "x"), "not proven")

    def test_refund_decision(self):
        rows = lesson.load_rows(os.path.join(HERE, "data", "tickets.csv"))
        cm = lesson.confusion_matrix(rows, LABELS)
        p, r, _ = lesson.precision_recall_f1(cm, "refund")
        self.assertFalse(lesson.meets_rule(p, r), "refund precision is below 0.90, so the answer is no")
        self.assertEqual(lesson.decide(cm, "refund"), ref_decision(rows, "refund"))
        self.assertEqual(lesson.decide(cm, "refund"), "no",
                         "the upper end of the refund precision interval is below 0.90, so this is a firm no")

    def test_second_dataset(self):
        rows = make_data.build(seed=OTHER_SEED)["tickets"]
        cm = lesson.confusion_matrix(rows, LABELS)
        for a in LABELS:
            for p in LABELS:
                expected = sum(1 for r in rows if r["human_label"] == a and r["llm_label"] == p)
                self.assertEqual(cm[a][p], expected, "seed %d: cell %s -> %s" % (OTHER_SEED, a, p))
        right = sum(1 for r in rows if r["human_label"] == r["llm_label"])
        self.assertAlmostEqual(lesson.accuracy(cm), right / len(rows))
        for label in LABELS:
            self.assertEqual(lesson.decide(cm, label), ref_decision(rows, label),
                             "seed %d: decision for %s differs from the reference" % (OTHER_SEED, label))

    def test_fixture_is_consistent_and_labelled(self):
        # A model at temperature 0 gives one label per text. So must the simulation.
        for rows in (committed_rows(), make_data.build(seed=OTHER_SEED)["tickets"]):
            seen = {}
            for r in rows:
                self.assertEqual(seen.setdefault(r["text"], r["llm_label"]), r["llm_label"],
                                 "the same text got two LLM labels: %r" % r["text"])
        self.assertGreater(len({r["text"] for r in committed_rows()}), 300, "most tickets should be distinct texts")
        with open(os.path.join(HERE, "data", "fixture.json")) as f:
            info = json.load(f)
        self.assertEqual(info["llm_label_source"], "simulated")


if __name__ == "__main__":
    unittest.main()
