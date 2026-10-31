"""Tests for lesson 04: north star and guardrails. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Expected answers are computed here in plain Python. The rule is checked on hand-made
cases (big samples where noise is tiny, small samples where it is not, zeros), on the
committed data, and on a second dataset built with another seed."""
import csv
import importlib.util
import math
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "experiment.csv")
OTHER_SEED = 9
KEYS = ["users", "applying_users", "applications", "replies", "unsubscribes"]
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

BIG = 1000000  # so many users that the noise is tiny and the point estimates decide


def base(n=BIG, apps=BIG, **kw):
    d = {"north_star": 0.30, "reply_rate": 0.20, "unsubscribe_rate": 0.020, "users": n, "applications": apps}
    d.update(kw)
    return d


def half_width(p0, n0, p1, n1, z=1.96):
    return z * math.sqrt(p0 * (1 - p0) / n0 + p1 * (1 - p1) / n1)


def reference_decision(c, t, min_lift=0.02, max_reply_drop=0.02, max_unsub_rise=0.005):
    """The same rule written a second way: change against half-widths."""
    lift = t["north_star"] - c["north_star"]
    hw_ns = half_width(c["north_star"], c["users"], t["north_star"], t["users"])
    reply = t["reply_rate"] - c["reply_rate"]
    hw_reply = half_width(c["reply_rate"], c["applications"], t["reply_rate"], t["applications"])
    unsub = t["unsubscribe_rate"] - c["unsubscribe_rate"]
    hw_unsub = half_width(c["unsubscribe_rate"], c["users"], t["unsubscribe_rate"], t["users"])
    breaches = []
    if reply - hw_reply < -max_reply_drop:
        breaches.append("reply_rate")
    if unsub + hw_unsub > max_unsub_rise:
        breaches.append("unsubscribe_rate")
    ok = lift >= min_lift and lift - hw_ns > 0 and not breaches
    return "launch" if ok else "do not launch", breaches


def raw_summary(path):
    exp = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            s = exp.setdefault(row["variant"], [0, 0, 0, 0, 0])
            a = int(row["applications"])
            s[0] += 1
            s[1] += a > 0
            s[2] += a
            s[3] += int(row["replies"])
            s[4] += int(row["unsubscribed"])
    return exp


class TestInterval(unittest.TestCase):
    def test_known_values(self):
        change, low, high = m.diff_interval(0.20, 400, 0.25, 400)
        hw = 1.96 * math.sqrt(0.2 * 0.8 / 400 + 0.25 * 0.75 / 400)
        self.assertAlmostEqual(change, 0.05)
        self.assertAlmostEqual(low, 0.05 - hw, msg="low end should be change - z x se")
        self.assertAlmostEqual(high, 0.05 + hw)

    def test_zero_n_is_none(self):
        self.assertIsNone(m.diff_interval(0.2, 0, 0.3, 100), "with no observations there is no interval: return None")
        self.assertIsNone(m.diff_interval(0.2, 100, 0.0, 0))

    def test_zero_variance(self):
        self.assertEqual(m.diff_interval(0.0, 50, 0.0, 50), (0.0, 0.0, 0.0), "no events in either arm: change and interval are all 0")


class TestRule(unittest.TestCase):
    def test_clean_win_launches(self):
        r = m.decide(base(), base(north_star=0.33, reply_rate=0.19, unsubscribe_rate=0.022))
        self.assertEqual(r["decision"], "launch")
        self.assertEqual(r["breaches"], [])
        self.assertAlmostEqual(r["north_star_lift"], 0.03)
        self.assertEqual(sorted(r["intervals"]), ["north_star", "reply_rate", "unsubscribe_rate"])

    def test_small_lift_does_not_launch(self):
        r = m.decide(base(), base(north_star=0.31))
        self.assertEqual(r["decision"], "do not launch", "a 1 point lift is below the 2 point minimum, however precise")
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

    def test_noisy_win_does_not_launch(self):
        # Same point estimates as the clean win, but only 300 users and 300 applications per arm.
        c, t = base(300, 300), base(300, 300, north_star=0.33, reply_rate=0.19, unsubscribe_rate=0.022)
        r = m.decide(c, t)
        self.assertEqual(r["decision"], "do not launch",
                         "with 300 users per arm a 3 point lift could be noise: the north star interval must be above 0")
        self.assertLessEqual(r["intervals"]["north_star"][1], 0)

    def test_noisy_guardrail_is_a_breach(self):
        # Reply rate fell only 1 point (inside the 2 point tolerance), but on 500 applications per arm
        # the interval reaches far below -2 points, so the rule cannot call it safe.
        c, t = base(apps=500), base(apps=500, north_star=0.36, reply_rate=0.19)
        r = m.decide(c, t)
        self.assertEqual(r["breaches"], ["reply_rate"],
                         "a guardrail passes only if its whole interval stays inside the tolerance")

    def test_zero_applications_fails_the_reply_guardrail(self):
        r = m.decide(base(), base(apps=0, north_star=0.40, reply_rate=0.0))
        self.assertIn("reply_rate", r["breaches"], "no applications means the reply rate cannot be checked, so it fails")
        self.assertEqual(r["decision"], "do not launch")

    def test_metrics_zero_safe(self):
        z = m.metrics({"users": 0, "applying_users": 0, "applications": 0, "replies": 0, "unsubscribes": 0})
        self.assertEqual(z, {"north_star": 0.0, "reply_rate": 0.0, "unsubscribe_rate": 0.0, "users": 0, "applications": 0})


class OnDataChecks:
    def test_summarize(self):
        got = m.summarize(self.path)
        self.assertEqual(sorted(got), ["control", "quick_apply"])
        for v, vals in raw_summary(self.path).items():
            self.assertEqual([got[v][k] for k in KEYS], vals, "wrong summary for %s" % v)

    def test_metrics_and_decision(self):
        got = m.summarize(self.path)
        c, t = m.metrics(got["control"]), m.metrics(got["quick_apply"])
        u, ap, apps, rep, uns = raw_summary(self.path)["quick_apply"]
        self.assertAlmostEqual(t["north_star"], ap / u)
        self.assertAlmostEqual(t["reply_rate"], rep / apps)
        self.assertAlmostEqual(t["unsubscribe_rate"], uns / u)
        self.assertEqual((t["users"], t["applications"]), (u, apps))
        decision, breaches = reference_decision(c, t)
        r = m.decide(c, t)
        self.assertEqual(r["breaches"], breaches)
        self.assertEqual(r["decision"], decision)
        self.assertAlmostEqual(r["north_star_lift"], ap / u - c["north_star"])


class TestOnData(OnDataChecks, unittest.TestCase):
    path = DATA

    def test_lesson_story(self):
        got = m.summarize(DATA)
        r = m.decide(m.metrics(got["control"]), m.metrics(got["quick_apply"]))
        self.assertGreater(r["intervals"]["north_star"][1], 0, "the north star lift is not noise on the lesson data")
        self.assertLess(r["intervals"]["reply_rate"][2], -0.02, "even the top of the reply rate interval is past -2 points")
        self.assertEqual(r["breaches"], ["reply_rate", "unsubscribe_rate"])
        self.assertEqual(r["decision"], "do not launch")


class TestOnSecondDataset(OnDataChecks, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.path = os.path.join(cls.tmp, "experiment.csv")
        make_data.write_csv(make_data.build(seed=OTHER_SEED)["experiment"], cls.path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
