"""Tests for lesson 03: portfolio project end to end.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

The expected numbers are computed below in plain Python with datetime, on the committed CSV,
on a second dataset built in memory with another seed, and on tiny hand-made tables.
"""
import csv
import datetime
import importlib.util
import math
import os
import re
import sys
import unittest
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)

sys.path.insert(0, HERE)
import make_data  # noqa: E402

AS_OF = datetime.date(2026, 10, 1)
TRIAL_DAYS, WINDOW = 14, 90
SECTIONS = ["Question", "Data", "Method", "Result", "Recommendation", "Limitations"]


def committed_rows():
    with open(os.path.join(HERE, "data", "subscriptions.csv"), newline="") as f:
        return [[r["customer_id"], r["signup_date"], r["start_type"], r["plan"], r["cancel_date"]] for r in csv.DictReader(f)]


def day(s):
    return datetime.date.fromisoformat(s)


def expected_conversion(rows):
    starters = never = 0
    for _, signup, start, _, cancel in rows:
        if start != "trial" or (AS_OF - day(signup)).days < TRIAL_DAYS:
            continue
        starters += 1
        if cancel and (day(cancel) - day(signup)).days < TRIAL_DAYS:
            never += 1
    return (starters, never)


def expected_groups(rows):
    out = {}
    for _, signup, start, plan, cancel in rows:
        s = day(signup)
        c = day(cancel) if cancel else None
        if start == "trial":
            if c is not None and (c - s).days < TRIAL_DAYS:
                continue  # cancelled inside the trial: never a paying customer
            first_paid = s + datetime.timedelta(days=TRIAL_DAYS)
        else:
            first_paid = s
        if (AS_OF - first_paid).days < WINDOW:
            continue  # not 90 paid days of history yet
        churned = c is not None and (c - first_paid).days <= WINDOW
        n, k = out.get((plan, start), (0, 0))
        out[(plan, start)] = (n + 1, k + int(churned))
    return out


def totals(groups):
    out = {}
    for (_, t), (n, c) in groups.items():
        a, b = out.get(t, (0, 0))
        out[t] = (a + n, b + c)
    return out


def ref_test(x1, n1, x2, n2):
    p1, p2 = x1 / n1, x2 / n2
    pooled = (x1 + x2) / (n1 + n2)
    se0 = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se0 if se0 else 0.0
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    return {"p1": p1, "p2": p2, "diff": p1 - p2, "z": z, "p_value": math.erfc(abs(z) / math.sqrt(2)),
            "ci_low": p1 - p2 - 1.96 * se, "ci_high": p1 - p2 + 1.96 * se}


class TestQueries(unittest.TestCase):
    def check(self, rows, where):
        con = lesson.load_db(rows=rows)
        self.assertEqual(lesson.conversion(con), expected_conversion(rows),
                         "%s: trial starters with 14 days of history, and how many cancelled inside the trial" % where)
        self.assertEqual(lesson.pull(con), expected_groups(rows),
                         "%s: paying customers only, 90 days from the first paid day (signup + 14 for a trial)" % where)

    def test_committed_data(self):
        self.check(committed_rows(), "committed data")

    def test_second_dataset(self):
        self.check([[str(v) for v in r] for r in make_data.build(seed=77)], "second dataset (seed 77)")

    def test_trial_boundaries(self):
        rows = [
            [1, "2026-03-01", "trial", "monthly", "2026-03-14"],  # day 13: inside the trial, never paid
            [2, "2026-03-01", "trial", "monthly", "2026-03-15"],  # day 14: first paid day, paid churn
            [3, "2026-03-01", "trial", "monthly", ""],            # still paying
            [4, "2026-06-20", "trial", "monthly", ""],            # first paid 4 Jul: under 90 paid days
            [5, "2026-09-25", "trial", "monthly", ""],            # 6 days old: trial not over
        ]
        con = lesson.load_db(rows=rows)
        self.assertEqual(lesson.conversion(con), (4, 1),
                         "4 trial starters had 14 days; only the day 13 cancel never paid")
        self.assertEqual(lesson.pull(con), {("monthly", "trial"): (2, 1)},
                         "customers 2 and 3 paid for 90 days; customer 2 cancelled on the first paid day")

    def test_paid_boundaries(self):
        rows = [
            [1, "2026-03-01", "paid", "annual", "2026-05-30"],    # day 90: churned
            [2, "2026-03-01", "paid", "annual", "2026-05-31"],    # day 91: not churned in the window
            [3, "2026-07-10", "paid", "annual", "2026-07-20"],    # under 90 days of history: left out
        ]
        self.assertEqual(lesson.pull(lesson.load_db(rows=rows)), {("annual", "paid"): (2, 1)},
                         "a cancel on day 90 counts, day 91 does not, and recent signups are left out")


class TestStatistics(unittest.TestCase):
    def test_two_proportion_test(self):
        t = lesson.two_proportion_test(60, 200, 40, 200)
        r = ref_test(60, 200, 40, 200)
        for k in r:
            self.assertAlmostEqual(t[k], r[k], places=6, msg="key %s for 60/200 against 40/200" % k)

    def test_equal_rates(self):
        same = lesson.two_proportion_test(50, 200, 50, 200)
        self.assertAlmostEqual(same["z"], 0.0)
        self.assertAlmostEqual(same["p_value"], 1.0)

    def test_zero_churn(self):
        t = lesson.two_proportion_test(0, 40, 0, 50)
        self.assertEqual((t["z"], t["p_value"]), (0.0, 1.0),
                         "nobody churned in either group: the pooled standard error is 0, so return z 0 and p 1")
        self.assertEqual((t["ci_low"], t["ci_high"]), (0.0, 0.0))


class TestWriteUpAndChart(unittest.TestCase):
    def setUp(self):
        rows = committed_rows()
        self.conv, self.groups = expected_conversion(rows), expected_groups(rows)
        g = totals(self.groups)
        self.test = ref_test(g["trial"][1], g["trial"][0], g["paid"][1], g["paid"][0])
        self.text = lesson.write_up(self.conv, self.groups, self.test)

    def test_sections_and_counts(self):
        text = self.text
        self.assertEqual(re.findall(r"^## (.+)$", text, re.M), SECTIONS, "the write-up needs these sections, in this order")
        starters, never = self.conv
        self.assertIn("%d of %d" % (never, starters), text, "give trial conversion as counts: never paid of trial starters")
        for t, (n, c) in totals(self.groups).items():
            self.assertIn("%d of %d" % (c, n), text, "the Result section should give paid churn counts for %s" % t)
        for (plan, t), (n, c) in self.groups.items():
            self.assertIn("%d of %d" % (c, n), text, "give the within-plan counts for %s, %s" % (plan, t))
        self.assertIn("%.1f%%" % (100 * self.test["p1"]), text)
        self.assertIn("%.1f%%" % (100 * self.test["p2"]), text)
        self.assertIn("](diagram.svg)", text, "show the chart on the page")
        limits = text.split("## Limitations", 1)[1]
        self.assertGreaterEqual(limits.count("\n- "), 2, "list at least two limitations")
        self.assertRegex(limits.lower(), r"experiment|observational|causal", "say that this comparison is not an experiment")
        self.assertNotRegex(limits.lower(), r"should be repeated within",
                            "the within-plan comparison is done: report it in Result, not as a limitation")
        self.assertLess(len(text.split()), 450, "one page: keep it short")

    def test_chart(self):
        svg = lesson.churn_chart_svg(self.groups)
        root = ET.fromstring(svg)
        titles = [el.text for el in root.iter("{http://www.w3.org/2000/svg}title")]
        want = sorted("%s, %s: %.1f%% (%d of %d)" % (plan, t, 100.0 * c / n, c, n) for (plan, t), (n, c) in self.groups.items())
        self.assertEqual(sorted(titles), want, "one bar per plan and start type, labelled with its rate and counts")
        with open(os.path.join(HERE, "diagram.svg")) as f:
            self.assertEqual(f.read(), svg, "diagram.svg is out of date: run python3 solution/solution.py")


if __name__ == "__main__":
    unittest.main()
