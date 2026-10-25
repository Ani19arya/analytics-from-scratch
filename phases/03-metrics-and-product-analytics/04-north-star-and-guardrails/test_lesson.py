"""Tests for lesson 04: north star and guardrails. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead."""
import csv
import importlib.util
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


def base(**kw):
    d = {"north_star": 0.30, "reply_rate": 0.20, "unsubscribe_rate": 0.020}
    d.update(kw)
    return d


class TestRule(unittest.TestCase):
    def test_clean_win_launches(self):
        r = m.decide(base(), base(north_star=0.33, reply_rate=0.19, unsubscribe_rate=0.022))
        self.assertEqual(r["decision"], "launch")
        self.assertEqual(r["breaches"], [])
        self.assertAlmostEqual(r["north_star_lift"], 0.03)

    def test_small_lift_does_not_launch(self):
        r = m.decide(base(), base(north_star=0.31))
        self.assertEqual(r["decision"], "do not launch")
        self.assertEqual(r["breaches"], [])

    def test_guardrail_blocks_a_winner(self):
        r = m.decide(base(), base(north_star=0.40, reply_rate=0.15))
        self.assertEqual(r["decision"], "do not launch")
        self.assertEqual(r["breaches"], ["reply_rate"])
        r = m.decide(base(), base(north_star=0.40, reply_rate=0.10, unsubscribe_rate=0.030))
        self.assertEqual(r["breaches"], ["reply_rate", "unsubscribe_rate"])

    def test_better_guardrail_is_fine(self):
        r = m.decide(base(), base(north_star=0.35, reply_rate=0.25, unsubscribe_rate=0.010))
        self.assertEqual(r["decision"], "launch")

    def test_tolerances_are_parameters(self):
        r = m.decide(base(), base(north_star=0.40, reply_rate=0.15), max_reply_drop=0.10)
        self.assertEqual(r["decision"], "launch")

    def test_metrics_zero_safe(self):
        z = m.metrics({"users": 0, "applying_users": 0, "applications": 0, "replies": 0, "unsubscribes": 0})
        self.assertEqual(z, {"north_star": 0.0, "reply_rate": 0.0, "unsubscribe_rate": 0.0})


class TestOnData(unittest.TestCase):
    def setUp(self):
        exp = {}
        with open(DATA, newline="") as f:
            for row in csv.DictReader(f):
                s = exp.setdefault(row["variant"], [0, 0, 0, 0, 0])
                a = int(row["applications"])
                s[0] += 1
                s[1] += a > 0
                s[2] += a
                s[3] += int(row["replies"])
                s[4] += int(row["unsubscribed"])
        self.expected = exp

    def test_summarize(self):
        got = m.summarize(DATA)
        self.assertEqual(sorted(got), ["control", "quick_apply"])
        keys = ["users", "applying_users", "applications", "replies", "unsubscribes"]
        for v, vals in self.expected.items():
            self.assertEqual([got[v][k] for k in keys], vals, "wrong summary for %s" % v)

    def test_metrics_and_decision(self):
        got = m.summarize(DATA)
        c, t = m.metrics(got["control"]), m.metrics(got["quick_apply"])
        u, ap, apps, rep, uns = self.expected["quick_apply"]
        self.assertAlmostEqual(t["north_star"], ap / u)
        self.assertAlmostEqual(t["reply_rate"], rep / apps)
        self.assertAlmostEqual(t["unsubscribe_rate"], uns / u)
        r = m.decide(c, t)
        self.assertGreater(r["north_star_lift"], 0.02, "quick apply should move the north star")
        self.assertEqual(r["breaches"], ["reply_rate"])
        self.assertEqual(r["decision"], "do not launch")


if __name__ == "__main__":
    unittest.main()
