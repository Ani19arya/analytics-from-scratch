"""Tests for lesson 07-08: the metrics case interview.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

The expected answers are worked out below in plain Python, separately from the lesson code.
Your diagnose runs on the committed data and on data built in memory from other seeds,
where the planted cause is different, so an answer typed in by hand cannot pass.
"""
import csv
import importlib.util
import math
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)

sys.path.insert(0, HERE)
import make_data  # noqa: E402

SPLIT = "2026-10-19"
LABELS = ["Clarify:", "Check the data:", "Break it down:", "Segment:", "Cause:", "Next step:"]
STEP_WORDS = {"visits": "visits", "start_rate": "start rate", "finish_rate": "finish rate"}


def read(name):
    with open(os.path.join(HERE, "data", name), newline="") as f:
        return list(csv.DictReader(f))


def as_dicts(header, rows):
    return [dict(zip(header, [str(x) for x in r])) for r in rows]


def seeded(seed):
    d = make_data.build(seed)
    return as_dicts(make_data.FUNNEL_HEADER, d["funnel"]), as_dicts(make_data.ACCOUNTS_HEADER, d["accounts"]), d["truth"]


def totals(rows, keep=lambda r: True):
    """{week: [visits, starts, signups]} with week 0 = prior, 1 = current."""
    t = {0: [0, 0, 0], 1: [0, 0, 0]}
    for r in rows:
        if keep(r):
            w = t[int(r["date"] >= SPLIT)]
            w[0] += int(r["visits"])
            w[1] += int(r["signup_starts"])
            w[2] += int(r["signups"])
    return t


def ref_diagnose(funnel, accounts):
    """The case, worked out a second way."""
    ev, ac = {}, {}
    for r in funnel:
        if r["date"] >= SPLIT:
            ev[r["app_version"]] = ev.get(r["app_version"], 0) + int(r["signups"])
    for r in accounts:
        if r["date"] >= SPLIT:
            ac[r["app_version"]] = ac.get(r["app_version"], 0) + int(r["accounts"])
    broken = sorted((ev.get(v, 0) / n, v) for v, n in ac.items() if n and ev.get(v, 0) / n < 0.8)
    if broken:
        return {"cause": "tracking", "dimension": "app_version", "segment": broken[0][1], "step": None}
    candidates = []
    for rank, dim in enumerate(("platform", "channel")):
        for value in sorted({r[dim] for r in funnel}):
            t = totals(funnel, lambda r, d=dim, v=value: r[d] == v)
            candidates.append((t[1][2] - t[0][2], rank, value, dim, t))
    change, _, value, dim, t = min(candidates)
    # Every LMDI effect has the same positive weight, so the most negative effect is the
    # step whose current / prior ratio is smallest.
    p, c = t[0], t[1]
    ratios = {"visits": c[0] / p[0], "start_rate": (c[1] / c[0]) / (p[1] / p[0]),
              "finish_rate": (c[2] / c[1]) / (p[2] / p[1])}
    step = min(("visits", "start_rate", "finish_rate"), key=lambda s: (ratios[s], s != "visits"))
    return {"cause": "traffic" if step == "visits" else "conversion", "dimension": dim, "segment": value, "step": step}


def week(visits, starts, signups):
    return {"visits": visits, "starts": starts, "signups": signups}


def funnel_row(date, platform, version, channel, visits, starts, signups):
    return {"date": date, "platform": platform, "app_version": version, "channel": channel,
            "visits": str(visits), "signup_starts": str(starts), "signups": str(signups)}


class TestDecompose(unittest.TestCase):
    def test_effects_add_up(self):
        prior, current = week(10000, 1200, 640), week(10100, 1190, 500)
        e = lesson.decompose(prior, current)
        self.assertEqual(e["total"], -140, "total is current sign-ups minus prior sign-ups")
        self.assertAlmostEqual(e["visits"] + e["start_rate"] + e["finish_rate"], -140, places=6,
                               msg="the three effects must add up exactly to the total change")
        w = (500 - 640) / (math.log(500) - math.log(640))
        self.assertAlmostEqual(e["finish_rate"], w * math.log((500 / 1190) / (640 / 1200)), places=6,
                               msg="effect = L(current, prior) * ln(current rate / prior rate), with L the logarithmic mean")

    def test_only_visits_move(self):
        e = lesson.decompose(week(1000, 100, 50), week(2000, 200, 100))
        self.assertAlmostEqual(e["visits"], 50, places=6, msg="when only visits double, visits explain the whole change")
        self.assertAlmostEqual(e["start_rate"], 0, places=6)
        self.assertAlmostEqual(e["finish_rate"], 0, places=6)

    def test_no_change(self):
        e = lesson.decompose(week(1000, 100, 50), week(1000, 100, 50))
        self.assertEqual(e["total"], 0)
        for s in ("visits", "start_rate", "finish_rate"):
            self.assertAlmostEqual(e[s], 0, places=9, msg="equal weeks give 0 for every step (log_mean(a, a) is a)")

    def test_zero_gives_none(self):
        e = lesson.decompose(week(0, 0, 0), week(500, 60, 30))
        self.assertEqual(e["total"], 30, "the total is still current minus prior")
        self.assertEqual([e["visits"], e["start_rate"], e["finish_rate"]], [None, None, None],
                         "a segment with 0 in either week has no logs: return None for the three steps")


class TestTrackingGaps(unittest.TestCase):
    def test_hand_made(self):
        funnel = [funnel_row("2026-10-20", "web", "web", "organic", 900, 100, 50),
                  funnel_row("2026-10-20", "ios", "ios-4.9", "organic", 300, 50, 3),
                  funnel_row("2026-10-12", "ios", "ios-4.8", "organic", 300, 50, 30)]
        accounts = [{"date": "2026-10-20", "app_version": "web", "accounts": "51"},
                    {"date": "2026-10-20", "app_version": "ios-4.9", "accounts": "30"},
                    {"date": "2026-10-20", "app_version": "android-5.2", "accounts": "20"},
                    {"date": "2026-10-20", "app_version": "ios-4.8", "accounts": "0"},
                    {"date": "2026-10-12", "app_version": "ios-4.8", "accounts": "30"}]
        self.assertEqual(lesson.tracking_gaps(funnel, accounts), [("android-5.2", 0.0), ("ios-4.9", 0.1)],
                         "flag versions with events below 0.8 x accounts in the current week, lowest first; a version with "
                         "accounts but no event rows has ratio 0, and a version with 0 accounts is skipped")

    def test_empty(self):
        self.assertEqual(lesson.tracking_gaps([], []), [], "no rows, no gaps")

    def test_committed_has_none(self):
        self.assertEqual(lesson.tracking_gaps(read("funnel_daily.csv"), read("accounts_daily.csv")), [],
                         "on the committed data events and accounts agree for every version")


class TestSegmentChanges(unittest.TestCase):
    def test_hand_made(self):
        rows = [funnel_row("2026-10-12", "web", "web", "organic", 10, 5, 4),
                funnel_row("2026-10-19", "web", "web", "organic", 10, 5, 1),
                funnel_row("2026-10-12", "ios", "ios-4.8", "organic", 10, 5, 3),
                funnel_row("2026-10-19", "ios", "ios-4.9", "organic", 10, 5, 3),
                funnel_row("2026-10-19", "android", "android-5.2", "referral", 10, 5, 2),
                funnel_row("2026-10-12", "android", "android-5.1", "referral", 10, 5, 5)]
        self.assertEqual(lesson.segment_changes(rows, "platform"),
                         [("android", 5, 2, -3), ("web", 4, 1, -3), ("ios", 3, 3, 0)],
                         "biggest drop first, ties sorted by value")
        self.assertEqual(lesson.segment_changes(rows, "app_version"),
                         [("android-5.1", 5, 0, -5), ("ios-4.8", 3, 0, -3), ("web", 4, 1, -3),
                          ("android-5.2", 0, 2, 2), ("ios-4.9", 0, 3, 3)],
                         "a value seen in only one week counts 0 in the other")

    def test_committed(self):
        rows = read("funnel_daily.csv")
        for dim in ("platform", "channel"):
            want = []
            for v in sorted({r[dim] for r in rows}):
                t = totals(rows, lambda r, d=dim, v=v: r[d] == v)
                want.append((v, t[0][2], t[1][2], t[1][2] - t[0][2]))
            want.sort(key=lambda x: (x[3], x[0]))
            self.assertEqual(lesson.segment_changes(rows, dim), want, "sign-ups by %s, prior and current week" % dim)


class TestDiagnose(unittest.TestCase):
    KEYS = ("cause", "dimension", "segment", "step")

    def check(self, funnel, accounts, where):
        got = lesson.diagnose(funnel, accounts)
        want = ref_diagnose(funnel, accounts)
        self.assertEqual({k: got.get(k) for k in self.KEYS}, want, "%s: the diagnosis does not match" % where)
        return got

    def test_committed(self):
        got = self.check(read("funnel_daily.csv"), read("accounts_daily.csv"), "committed data")
        t = totals(read("funnel_daily.csv"))
        web = totals(read("funnel_daily.csv"), lambda r: r["platform"] == "web")
        self.assertAlmostEqual(got["share"], round((web[1][2] - web[0][2]) / (t[1][2] - t[0][2]), 2), places=6,
                               msg="share is the segment's change divided by the total change, rounded to 2 places")

    def test_other_seeds(self):
        causes = set()
        for seed in (3, 2, 1, 0, 5):
            funnel, accounts, truth = seeded(seed)
            want = ref_diagnose(funnel, accounts)
            self.assertEqual(want, truth, "the test's own reference disagrees with the planted cause for seed %d" % seed)
            self.check(funnel, accounts, "seed %d (planted: %s in %s)" % (seed, truth["cause"], truth["segment"]))
            causes.add(truth["cause"])
        self.assertEqual(causes, {"tracking", "traffic", "conversion"}, "the seeds should cover all three causes")


class TestAnswer(unittest.TestCase):
    def test_answer_follows_the_case(self):
        text = lesson.ANSWER
        self.assertTrue(text.strip(), "write your spoken answer in ANSWER, one line per step")
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        found = []
        for label in LABELS:
            hits = [i for i, x in enumerate(lines) if x.startswith(label)]
            self.assertTrue(hits, "ANSWER needs a line that starts with '%s'" % label)
            body = lines[hits[0]][len(label):]
            self.assertGreaterEqual(len(body.split()), 5, "say more than a few words after '%s'" % label)
            found.append(hits[0])
        self.assertEqual(found, sorted(found), "keep the steps in order: %s" % ", ".join(LABELS))
        by_label = {label: lines[i] for label, i in zip(LABELS, found)}
        self.assertIn("accounts", by_label["Check the data:"].lower(),
                      "the data check compares the events with accounts in the database: say so")
        t = totals(read("funnel_daily.csv"))
        nums = [n.replace(",", "") for n in re.findall(r"\d[\d,]*", by_label["Break it down:"])]
        for n in (t[0][2], t[1][2]):
            self.assertIn(str(n), nums, "the 'Break it down:' line should give sign-ups in both weeks (%d and %d)" % (t[0][2], t[1][2]))
        want = ref_diagnose(read("funnel_daily.csv"), read("accounts_daily.csv"))
        cause = by_label["Cause:"].lower()
        self.assertTrue(re.search(r"\b%s\b" % re.escape(want["segment"]), cause), "the 'Cause:' line should name the segment")
        self.assertIn(STEP_WORDS.get(want["step"], "tracking"), cause, "the 'Cause:' line should name the funnel step in words")


if __name__ == "__main__":
    unittest.main()
