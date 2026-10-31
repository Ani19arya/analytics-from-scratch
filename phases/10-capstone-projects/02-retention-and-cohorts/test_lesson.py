"""Checker for capstone 10-02: Chordwhistle retention and cohorts.
Run: python3 test_lesson.py           (checks exercise.py, your submission)
     CHECK_SOLUTION=1 python3 test_lesson.py   (checks solution/solution.py)

It checks the numbers that have one right answer. Every expected value is
computed here in plain Python from the raw rows, never read from the solution.
The checks run on the committed data, on a second dataset built in memory with
another seed (so typed-in answers fail), and on tiny hand-made tables. The
two-proportion test is checked two independent ways: z squared must equal the
chi-square statistic of the 2 x 2 table, and the p-value must agree with a
seeded permutation test. Judgement is scored with RUBRIC.md, not here.
"""
import csv
import importlib.util
import math
import os
import random
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OTHER_SEED = 9
LAST = "2026-09"
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")

spec = importlib.util.spec_from_file_location("submission", TARGET)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sys.path.insert(0, HERE)
import make_data  # noqa: E402


def read_rows(name):
    with open(os.path.join(DATA, name), newline="") as f:
        return list(csv.DictReader(f))


def u_row(uid, date, source="organic", platform="ios", account_type="customer"):
    return {"user_id": uid, "signup_date": date, "platform": platform, "source": source, "account_type": account_type}


def a_row(uid, month, lessons, loaded="2026-10-01"):
    return {"user_id": uid, "activity_month": month, "lessons_completed": str(lessons), "loaded_at": loaded}


def age(cohort, month):
    return (int(month[:4]) * 12 + int(month[5:7])) - (int(cohort[:4]) * 12 + int(cohort[5:7]))


# ---- an independent reference ---------------------------------------------

def ref_matrix(raw):
    cohort = {}
    for u in raw["users"]:
        if u["account_type"] == "customer":
            cohort[u["user_id"]] = u["signup_date"][:7]
    pairs = {(r["user_id"], r["activity_month"]) for r in raw["activity"]
             if int(r["lessons_completed"]) > 0 and r["activity_month"] <= LAST and r["user_id"] in cohort
             and r["activity_month"] >= cohort[r["user_id"]]}
    size, counts = {}, {}
    for uid, c in cohort.items():
        size[c] = size.get(c, 0) + 1
    for uid, month in pairs:
        key = (cohort[uid], age(cohort[uid], month))
        counts[key] = counts.get(key, 0) + 1
    return {c: (size[c], [counts.get((c, k), 0) for k in range(age(c, LAST) + 1)]) for c in size}, cohort, pairs


class TestHandMade(unittest.TestCase):
    def test_clean_users(self):
        raw = [u_row("a", "2026-01-05"), u_row("a", "2026-01-05"), u_row("s", "2026-01-02", account_type="staff"),
               u_row("b", "2026-02-28", source="paid_social", platform="android")]
        got = m.clean_users(raw)
        self.assertEqual(sorted(got), ["a", "b"], "one entry per user, and staff accounts are not users")
        self.assertEqual(got["b"], {"signup_month": "2026-02", "platform": "android", "source": "paid_social"})
        self.assertEqual(m.clean_users([]), {})

    def test_active_months_uses_lessons_not_rows(self):
        users = {"a": {"signup_month": "2026-03", "platform": "ios", "source": "organic"}}
        raw = [a_row("a", "2026-03", 2), a_row("a", "2026-03", 2), a_row("a", "2026-04", 0), a_row("a", "2026-05", 1),
               a_row("a", "2026-02", 3), a_row("a", "2026-10", 4), a_row("ghost", "2026-03", 5)]
        got = m.active_months(raw, users, "2026-09")
        self.assertEqual(got, {"a": {"2026-03", "2026-05"}},
                         "active = at least 1 lesson; a 0-lesson row (an app open) is not active; months after "
                         "the last complete month, before sign-up, or for unknown users are ignored")
        self.assertEqual(m.active_months([], users, "2026-09"), {"a": set()}, "a user with no rows is in, with no months")

    def test_retention_matrix_censoring(self):
        users = {"a": {"signup_month": "2026-07", "platform": "ios", "source": "organic"},
                 "b": {"signup_month": "2026-07", "platform": "ios", "source": "organic"},
                 "c": {"signup_month": "2026-09", "platform": "ios", "source": "organic"}}
        active = {"a": {"2026-07", "2026-09"}, "b": {"2026-08"}, "c": set()}
        got = m.retention_matrix(users, active, "2026-09")
        self.assertEqual(sorted(got), ["2026-07", "2026-09"])
        self.assertEqual(got["2026-07"]["active"], [1, 1, 1], "a July cohort is seen at months 0, 1 and 2 by September")
        self.assertEqual(got["2026-07"]["size"], 2)
        self.assertEqual(got["2026-07"]["rates"], [0.5, 0.5, 0.5])
        self.assertEqual(got["2026-09"]["active"], [0],
                         "a September cohort has only month 0: later months are not 0%, they are not observed yet")

    def test_pooled_curve_weights_by_size(self):
        matrix = {"A": {"size": 10, "active": [10, 5, 4], "rates": [1.0, 0.5, 0.4]},
                  "B": {"size": 30, "active": [30, 3], "rates": [1.0, 0.1]}}
        got = m.pooled_curve(matrix)
        self.assertEqual(len(got), 3)
        self.assertAlmostEqual(got[1], 8 / 40, msg="pool the counts (5 + 3) / (10 + 30), do not average the rates")
        self.assertAlmostEqual(got[2], 0.4, msg="month 2 uses only the cohorts observed at month 2")
        self.assertEqual(m.pooled_curve({}), [])

    def test_shortfall(self):
        matrix = {"A": {"size": 100, "active": [90, 40], "rates": [0.9, 0.4]},
                  "B": {"size": 100, "active": [90, 20], "rates": [0.9, 0.2]},
                  "C": {"size": 50, "active": [45, 20], "rates": [0.9, 0.4]},
                  "D": {"size": 10, "active": [9], "rates": [0.9]}}
        got = m.shortfall(matrix, 1)
        self.assertEqual([c for c, _ in got], ["B", "C", "A"],
                         "biggest loss first; D is not observed at month 1 so it is left out")
        self.assertAlmostEqual(dict(got)["B"], 100 * (60 / 150 - 0.2),
                               msg="B's baseline is the pooled rate of the OTHER cohorts, (40 + 20) / (100 + 50)")
        self.assertAlmostEqual(dict(got)["A"], 100 * (40 / 150 - 0.4))
        self.assertEqual(m.shortfall({"A": matrix["A"]}, 1), [], "one cohort has no others to compare with")

    def test_two_proportion_z(self):
        self.assertIsNone(m.two_proportion_z(0, 0, 5, 10), "an empty group: None")
        self.assertIsNone(m.two_proportion_z(0, 10, 0, 10), "no successes anywhere: SE is 0, so None")
        same = m.two_proportion_z(3, 10, 6, 20)
        self.assertAlmostEqual(same["z"], 0.0)
        self.assertAlmostEqual(same["p_value"], 1.0)
        got = m.two_proportion_z(20, 100, 40, 100)
        p = 0.3
        z = -0.2 / math.sqrt(p * (1 - p) * 0.02)
        self.assertAlmostEqual(got["diff"], -0.2)
        self.assertAlmostEqual(got["z"], z, places=9, msg="z uses the pooled proportion for the standard error")
        self.assertAlmostEqual(got["p_value"], math.erfc(abs(z) / math.sqrt(2)), places=9, msg="two-sided p-value")

    def test_retention_by_segment(self):
        users = {"a": {"signup_month": "2026-04", "platform": "ios", "source": "paid_social"},
                 "b": {"signup_month": "2026-04", "platform": "android", "source": "paid_social"},
                 "c": {"signup_month": "2026-04", "platform": "ios", "source": "organic"},
                 "d": {"signup_month": "2026-05", "platform": "ios", "source": "organic"}}
        active = {"a": {"2026-05"}, "b": set(), "c": {"2026-04"}, "d": {"2026-05"}}
        got = m.retention_by_segment(users, active, "2026-04", 1, "source")
        self.assertEqual(got, {"organic": {"size": 1, "active": 0, "rate": 0.0},
                               "paid_social": {"size": 2, "active": 1, "rate": 0.5}},
                         "month 1 of the April cohort is May; d is in another cohort")


class OnDataMixin:
    @classmethod
    def setUpClass(cls):
        cls.raw = cls.get_raw()
        cls.exp, cls.cohort, cls.pairs = ref_matrix(cls.raw)
        cls.users = m.clean_users(cls.raw["users"])
        cls.active = m.active_months(cls.raw["activity"], cls.users, LAST)
        cls.matrix = m.retention_matrix(cls.users, cls.active, LAST)

    def test_users_and_matrix(self):
        self.assertEqual(len(self.users), len(self.cohort), "distinct customer users (no duplicates, no staff)")
        self.assertEqual(sorted(self.matrix), sorted(self.exp), "one row per sign-up month")
        for c, (size, counts) in self.exp.items():
            self.assertEqual(self.matrix[c]["size"], size, c + ": cohort size")
            self.assertEqual(self.matrix[c]["active"], counts,
                             c + ": active users at each month; check the lessons >= 1 rule, duplicates and censoring")

    def test_pooled_curve(self):
        got = m.pooled_curve(self.matrix)
        longest = max(len(v[1]) for v in self.exp.values())
        self.assertEqual(len(got), longest)
        for k in range(longest):
            rows = [v for v in self.exp.values() if len(v[1]) > k]
            self.assertAlmostEqual(got[k], sum(v[1][k] for v in rows) / sum(v[0] for v in rows), places=9,
                                   msg="pooled retention at month %d" % k)

    def test_shortfall_and_story(self):
        got = m.shortfall(self.matrix, 1)
        exp = []
        for c, (size, counts) in self.exp.items():
            if len(counts) < 2:
                continue
            others = [v for o, v in self.exp.items() if o != c and len(v[1]) > 1]
            base = sum(v[1][1] for v in others) / sum(v[0] for v in others)
            exp.append((round(size * (base - counts[1] / size), 6), c))
        exp.sort(key=lambda t: (-t[0], t[1]))
        self.assertEqual([c for c, _ in got], [c for _, c in exp], "cohorts ranked by month-1 users lost")
        for (c, lost), (e, _) in zip(got, exp):
            self.assertAlmostEqual(lost, e, places=5, msg=c + ": users lost at month 1")
        self.assertIn(got[0][0], ("2026-04", "2026-05"), "the planted story: a campaign cohort loses the most users")
        seg = m.retention_by_segment(self.users, self.active, got[0][0], 1, "source")
        self.assertLess(seg["paid_social"]["rate"], seg["organic"]["rate"],
                        "the planted story: paid social users drop off after month 0")

    def test_two_proportion_against_chi_square_and_permutation(self):
        top = m.shortfall(self.matrix, 1)[0][0]
        size, counts = self.exp[top]
        rest = [v for c, v in self.exp.items() if c != top and len(v[1]) > 1]
        x1, n1 = counts[1], size
        x2, n2 = sum(v[1][1] for v in rest), sum(v[0] for v in rest)
        got = m.two_proportion_z(x1, n1, x2, n2)
        table = [[x1, n1 - x1], [x2, n2 - x2]]
        total = n1 + n2
        chi2 = 0.0
        for i, row_total in enumerate((n1, n2)):
            for j, col_total in enumerate((x1 + x2, total - x1 - x2)):
                e = row_total * col_total / total
                chi2 += (table[i][j] - e) ** 2 / e
        self.assertAlmostEqual(got["z"] ** 2, chi2, places=6, msg="z squared must equal the 2 x 2 chi-square statistic")
        rng = random.Random(10)
        pool = [1] * (x1 + x2) + [0] * (total - x1 - x2)
        observed = abs(x1 / n1 - x2 / n2)
        hits, draws = 0, 4000
        for _ in range(draws):
            s1 = sum(rng.sample(pool, n1))
            if abs(s1 / n1 - (x1 + x2 - s1) / n2) >= observed - 1e-12:
                hits += 1
        self.assertLess(abs(got["p_value"] - (hits + 1) / (draws + 1)), 0.02,
                        "the p-value should agree with a permutation test (%.4f)" % ((hits + 1) / (draws + 1)))
        self.assertLess(got["p_value"], 0.05, "the planted campaign cohort is clearly below the others")


class TestOnData(OnDataMixin, unittest.TestCase):
    @staticmethod
    def get_raw():
        return {"users": read_rows("users.csv"), "activity": read_rows("activity.csv")}


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @staticmethod
    def get_raw():
        return make_data.build(seed=OTHER_SEED)


if __name__ == "__main__":
    unittest.main()
