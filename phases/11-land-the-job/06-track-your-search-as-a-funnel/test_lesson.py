"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py.

Expected answers are worked out here a second way: each row gets a status from date objects
in one pass, the Wilson interval comes from the roots of its quadratic (a different algebra
from the usual centre and half width), and channel numbers are rebuilt from those. Everything
runs on the committed log and on a second log built in memory from another seed.
"""
import csv
import datetime
import importlib.util
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

OTHER_SEED = 2024
AS_OF = "2026-10-31"
CHANNELS = ["careers_page", "job_board", "recruiter", "referral"]


def d(s):
    return datetime.date(*map(int, s.split("-")))


def ref_wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 1.0
    p = k / n
    a, b = 2 * n * p + z * z, z * math.sqrt(z * z + 4 * n * p * (1 - p))
    return max(0.0, (a - b) / (2 * (n + z * z))), min(1.0, (a + b) / (2 * (n + z * z)))


def ref_stage(apps, f, t, wait):
    status = []
    for a in apps:
        if not a[f]:
            continue
        if a[t]:
            status.append("pass")
        elif a["rejected_on"] or (d(AS_OF) - d(a[f])).days >= wait:
            status.append("fail")
        else:
            status.append("wait")
    return {"k": status.count("pass"), "n": status.count("pass") + status.count("fail"), "waiting": status.count("wait")}


def app(applied, reply="", interview="", offer="", rejected="", channel="job_board", hours="1.0"):
    return {"app_id": "T", "company": "Testco", "channel": channel, "applied_on": applied, "reply_on": reply,
            "interview_on": interview, "offer_on": offer, "rejected_on": rejected, "hours_spent": hours}


def stats(per_10h, low_10h, high_10h, n=5):
    return {"n": n, "per_10h": per_10h, "low_10h": low_10h, "high_10h": high_10h}


class TestWilson(unittest.TestCase):
    def test_known_values(self):
        low, high = lesson.wilson(2, 5)
        self.assertAlmostEqual(low, 0.1176, places=4, msg="2 of 5 should give about 12% to 77%")
        self.assertAlmostEqual(high, 0.7693, places=4)
        self.assertEqual(lesson.wilson(0, 0), (0.0, 1.0), "with no data, anything from 0 to 1 is possible")

    def test_edges_and_many(self):
        low, high = lesson.wilson(0, 7)
        self.assertAlmostEqual(low, 0.0, msg="0 successes: the lower bound is 0")
        self.assertGreater(high, 0.3, "0 of 7 still allows a rate above 30%")
        low, high = lesson.wilson(7, 7)
        self.assertAlmostEqual(high, 1.0)
        self.assertLess(low, 0.7, "7 of 7 does not prove a rate near 100%")
        for k, n in [(1, 3), (3, 6), (1, 21), (12, 40), (50, 60)]:
            got, want = lesson.wilson(k, n), ref_wilson(k, n)
            self.assertAlmostEqual(got[0], want[0], msg="lower bound for %d of %d" % (k, n))
            self.assertAlmostEqual(got[1], want[1], msg="upper bound for %d of %d" % (k, n))


class TestCensoring(unittest.TestCase):
    def test_stage_counts_by_hand(self):
        rows = [app("2026-10-01", reply="2026-10-05"),          # replied
                app("2026-10-10"),                              # 21 days old, no reply: failed
                app("2026-10-11"),                              # 20 days old: still waiting
                app("2026-10-28", reply="2026-10-29"),          # replied fast
                app("2026-10-29", rejected="2026-10-30", reply="2026-10-30"),
                app("2026-10-30")]                              # waiting
        self.assertEqual(lesson.stage_counts(rows, "applied_on", "reply_on", AS_OF, 21),
                         {"k": 3, "n": 4, "waiting": 2},
                         "an application exactly 21 days old with no reply has failed; younger ones are waiting")
        self.assertEqual(lesson.stage_counts(rows, "reply_on", "interview_on", AS_OF, 21),
                         {"k": 0, "n": 2, "waiting": 1},
                         "only rows that reached the first stage count; a rejection is final even when recent")
        self.assertEqual(lesson.stage_counts([], "applied_on", "reply_on", AS_OF, 21), {"k": 0, "n": 0, "waiting": 0})

    def test_funnel_shape(self):
        rows = [app("2026-09-01", reply="2026-09-03", interview="2026-09-08", offer="2026-09-20")]
        f = lesson.funnel(rows, AS_OF, 21)
        self.assertEqual([(a, b) for a, b, _ in f],
                         [("applied_on", "reply_on"), ("reply_on", "interview_on"), ("interview_on", "offer_on")])
        self.assertTrue(all(c == {"k": 1, "n": 1, "waiting": 0} for _, _, c in f))

    def test_replied_within(self):
        rows = [app("2026-10-01", reply="2026-10-15"), app("2026-10-01", reply="2026-10-16"),
                app("2026-10-17", reply="2026-10-18"), app("2026-10-18", reply="2026-10-19"), app("2026-10-02")]
        self.assertEqual(lesson.replied_within(rows, 14, AS_OF), (2, 4),
                         "count only applications at least 14 days old; a reply on day 14 counts, day 15 does not")
        self.assertEqual(lesson.replied_within([], 14, AS_OF), (0, 0))


class TestRecommend(unittest.TestCase):
    def test_clear_and_unclear(self):
        self.assertEqual(lesson.recommend({"a": stats(5.0, 3.0, 8.0), "b": stats(1.0, 0.2, 2.5)}),
                         {"best": "a", "confident": True})
        self.assertEqual(lesson.recommend({"a": stats(5.0, 2.0, 8.0), "b": stats(1.0, 0.2, 2.5)}),
                         {"best": "a", "confident": False}, "overlapping intervals are not clear evidence")
        self.assertEqual(lesson.recommend({"a": stats(2.0, 1.0, 3.0), "b": stats(2.0, 1.0, 3.0)})["best"], "a",
                         "on a tie, take the first channel by name")
        self.assertEqual(lesson.recommend({"a": stats(None, 0.0, 9.0, n=0), "b": stats(1.0, 0.5, 2.0)}),
                         {"best": "b", "confident": True}, "a channel with nothing decided yet is left out")
        self.assertIsNone(lesson.recommend({}))


class TestOnData(unittest.TestCase):
    def check(self, apps, label):
        for (f, t, got), (wf, wt) in zip(lesson.funnel(apps, AS_OF, 21),
                                         [("applied_on", "reply_on"), ("reply_on", "interview_on"), ("interview_on", "offer_on")]):
            self.assertEqual(got, ref_stage(apps, wf, wt, 21), "%s: funnel step %s -> %s" % (label, wf, wt))
        old = [a for a in apps if (d(AS_OF) - d(a["applied_on"])).days >= 14]
        k = sum(1 for a in old if a["reply_on"] and (d(a["reply_on"]) - d(a["applied_on"])).days <= 14)
        self.assertEqual(lesson.replied_within(apps, 14, AS_OF), (k, len(old)), "%s: replied within 14 days" % label)
        s = lesson.by_channel(apps, AS_OF, 28)
        self.assertEqual(sorted(s), CHANNELS, "%s: one entry per channel" % label)
        want = {}
        for ch in CHANNELS:
            rows = [a for a in apps if a["channel"] == ch]
            c = ref_stage(rows, "applied_on", "interview_on", 28)
            hours = sum(float(a["hours_spent"]) for a in rows) / len(rows)
            low, high = ref_wilson(c["k"], c["n"])
            for key in ("k", "n", "waiting"):
                self.assertEqual(s[ch][key], c[key], "%s: %s %s (waiting rows are left out of n)" % (label, ch, key))
            self.assertEqual(s[ch]["apps"], len(rows))
            self.assertAlmostEqual(s[ch]["hours"], hours, msg="%s: %s mean hours over all its applications" % (label, ch))
            self.assertAlmostEqual(s[ch]["low"], low, msg="%s: %s Wilson low" % (label, ch))
            self.assertAlmostEqual(s[ch]["high"], high, msg="%s: %s Wilson high" % (label, ch))
            per = c["k"] / c["n"] * 10 / hours
            self.assertAlmostEqual(s[ch]["per_10h"], per, msg="%s: %s interviews per 10 hours" % (label, ch))
            self.assertAlmostEqual(s[ch]["low_10h"], low * 10 / hours)
            self.assertAlmostEqual(s[ch]["high_10h"], high * 10 / hours)
            want[ch] = (per, low * 10 / hours, high * 10 / hours)
        best = sorted(want, key=lambda ch: (-want[ch][0], ch))[0]
        clear = all(want[best][1] > want[o][2] for o in want if o != best)
        self.assertEqual(lesson.recommend(s), {"best": best, "confident": clear}, "%s: recommendation" % label)
        return s

    def test_committed_log(self):
        with open(os.path.join(HERE, "data", "applications.csv"), newline="") as f:
            apps = list(csv.DictReader(f))
        s = self.check(apps, "committed log")
        self.assertGreater(s["careers_page"]["waiting"], s["careers_page"]["n"],
                           "most career-page applications are recent and still waiting")

    def test_second_log(self):
        self.check(make_data.build(seed=OTHER_SEED)["applications"], "seed %d" % OTHER_SEED)


if __name__ == "__main__":
    unittest.main()
