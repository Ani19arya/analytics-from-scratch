"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py."""
import csv
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)

LABELS = ["billing", "bug", "refund", "other"]


def tiny_rows():
    pairs = [("a", "a"), ("a", "b"), ("b", "b"), ("b", "b"), ("b", "a")]
    return [{"human_label": h, "llm_label": p} for h, p in pairs]


class TestClassifierGrade(unittest.TestCase):
    def test_tiny_confusion_matrix(self):
        cm = lesson.confusion_matrix(tiny_rows(), ["a", "b"])
        self.assertEqual(cm, {"a": {"a": 1, "b": 1}, "b": {"a": 1, "b": 2}})

    def test_tiny_metrics(self):
        cm = lesson.confusion_matrix(tiny_rows(), ["a", "b"])
        p, r, f1 = lesson.precision_recall_f1(cm, "b")
        self.assertAlmostEqual(p, 2 / 3)
        self.assertAlmostEqual(r, 2 / 3)
        self.assertAlmostEqual(f1, 2 / 3)
        self.assertAlmostEqual(lesson.accuracy(cm), 3 / 5)

    def test_zero_division(self):
        cm = {"x": {"x": 0, "y": 3}, "y": {"x": 0, "y": 2}}
        self.assertEqual(lesson.precision_recall_f1(cm, "x"), (0.0, 0.0, 0.0))

    def test_full_data_matches_independent_count(self):
        with open(os.path.join(HERE, "data", "tickets.csv"), newline="") as f:
            rows = list(csv.DictReader(f))
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

    def test_rule(self):
        self.assertTrue(lesson.meets_rule(0.90, 0.80))
        self.assertFalse(lesson.meets_rule(0.95, 0.79))
        self.assertFalse(lesson.meets_rule(0.89, 0.99))

    def test_refund_decision(self):
        rows = lesson.load_rows(os.path.join(HERE, "data", "tickets.csv"))
        cm = lesson.confusion_matrix(rows, LABELS)
        p, r, _ = lesson.precision_recall_f1(cm, "refund")
        self.assertFalse(lesson.meets_rule(p, r), "refund precision is below 0.90, so the answer is no")


if __name__ == "__main__":
    unittest.main()
