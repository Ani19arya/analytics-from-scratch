"""Tests for case 02: SaaS churn. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Every expected number is computed here in plain Python from the CSV rows, never
with SQL and never read from the solution. The checks run on the committed data,
on a second dataset built in memory with another seed, and on tiny hand-made
tables (an active customer, a churn in the first month, a year boundary, a
segment with no match, nobody churned).
"""
import csv
import importlib.util
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "customers.csv")
OTHER_SEED = 12
AS_OF = "2026-10"
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")

spec = importlib.util.spec_from_file_location("lesson_module", TARGET)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sys.path.insert(0, HERE)
import make_data  # noqa: E402


def read_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def idx(month):
    return int(month[:4]) * 12 + int(month[5:7])


def tenure(r):
    return idx(r["churn_month"] or AS_OF) - idx(r["signup_month"])


def size(r):
    return "1-2" if int(r["seats"]) <= 2 else "3+"


def run_sql(con, sql):
    body = "\n".join(ln for ln in (sql or "").splitlines() if not ln.strip().startswith("--"))
    if not body.strip():
        raise AssertionError("the query is still a TODO: write it in the exercise file")
    return m.query(con, sql)


def tiny_db(rows):
    """rows: (signup_month, plan, seats, mrr, onboarded, churn_month or None)."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE customers (customer_id TEXT, signup_month TEXT, plan TEXT, seats INTEGER,"
                " mrr INTEGER, onboarded TEXT, churn_month TEXT)")
    con.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [("X%d" % i,) + tuple(r) for i, r in enumerate(rows)])
    return con


def seg(plan, onb, sz, churned, months, active, mrr, churned_mrr=0):
    return {"plan": plan, "onboarded": onb, "size": sz, "customers": churned + active, "churned": churned,
            "customer_months": months, "active_customers": active, "active_mrr": mrr, "churned_mrr": churned_mrr}


class TestHandMade(unittest.TestCase):
    def test_life_table(self):
        con = tiny_db([
            ("2026-08", "monthly", 1, 450, "yes", None),        # active: tenure 2
            ("2026-08", "monthly", 1, 450, "no", "2026-09"),    # left in its first month
            ("2025-12", "monthly", 1, 450, "yes", "2026-02"),   # across a year end: tenure 2
        ])
        got = [(r["plan"], r["tenure_month"], r["at_risk"], r["churned"], r["hazard_pct"]) for r in run_sql(con, m.LIFE_SQL)]
        self.assertEqual(got, [("monthly", 1, 3, 1, 33.33), ("monthly", 2, 2, 1, 50.0)],
                         "tenure counts months from signup to churn (or to 2026-10), across year ends; "
                         "at_risk in month n is everyone with tenure n or more")

    def test_segments(self):
        con = tiny_db([
            ("2026-01", "annual", 2, 750, "yes", None),
            ("2026-01", "annual", 3, 1125, "yes", "2026-04"),
            ("2026-09", "annual", 5, 1875, "yes", None),
        ])
        got = run_sql(con, m.SEGMENT_SQL)
        self.assertEqual([(g["size"], g["customers"], g["churned"], g["customer_months"], g["active_customers"],
                           g["active_mrr"], g["churned_mrr"]) for g in got],
                         [("1-2", 1, 0, 9, 1, 750, 0), ("3+", 2, 1, 4, 1, 1875, 1125)],
                         "2 seats is '1-2', 3 is '3+'; customer_months adds every tenure; MRR is split into active and churned")

    def test_survival(self):
        life = [{"plan": "monthly", "tenure_month": 2, "at_risk": 80, "churned": 8},
                {"plan": "monthly", "tenure_month": 1, "at_risk": 100, "churned": 20},
                {"plan": "monthly", "tenure_month": 3, "at_risk": 0, "churned": 0},
                {"plan": "annual", "tenure_month": 1, "at_risk": 5, "churned": 0}]
        got = m.survival(life, "monthly")
        self.assertEqual([t for t, _ in got], [1, 2], "stop at the first month with nobody at risk")
        self.assertAlmostEqual(got[1][1], 0.8 * 0.9, msg="survival multiplies (1 - hazard) month by month")
        self.assertEqual(m.survival(life, "annual"), [(1, 1.0)], "no churn: survival stays at 1")
        self.assertEqual(m.survival(life, "weekly"), [])

    def test_hazard(self):
        self.assertAlmostEqual(m.monthly_hazard(seg("monthly", "yes", "3+", 3, 100, 10, 0)), 0.03)
        self.assertIsNone(m.monthly_hazard(seg("monthly", "yes", "3+", 0, 0, 0, 0)), "no customer months: None, not 0")

    def test_lever(self):
        segs = [seg("monthly", "no", "3+", 10, 100, 20, 10000), seg("monthly", "yes", "3+", 2, 100, 50, 30000),
                seg("monthly", "no", "1-2", 1, 100, 5, 1000), seg("monthly", "yes", "1-2", 3, 100, 9, 900),
                seg("annual", "no", "3+", 1, 50, 4, 4000)]
        r = m.lever(segs, "onboarded", "no", "yes")
        self.assertAlmostEqual(r["mrr_kept"], 10000 * 0.08,
                               msg="only the gap to the matching segment counts; a segment already better (gap < 0) "
                                   "adds 0, and a segment with no match (annual, 3+, yes) is skipped")
        self.assertAlmostEqual(r["customers_kept"], 20 * 0.08)
        self.assertAlmostEqual(m.lever(segs, "size", "1-2", "3+")["mrr_kept"], 900 * 0.01,
                               msg="size lever: onboarded 1-2 seats churn 3% vs 2% (keeps 1% of 900); "
                                   "not onboarded 1-2 seats churn 1% vs 10% (keeps nothing)")

    def test_churn_shares(self):
        segs = [seg("monthly", "no", "1-2", 3, 10, 0, 0, 300), seg("monthly", "no", "3+", 1, 10, 0, 0, 900)]
        sh = m.churn_shares(segs, "size")
        self.assertAlmostEqual(sh["1-2"]["customers"], 0.75)
        self.assertAlmostEqual(sh["1-2"]["mrr"], 0.25, msg="a share of churned MRR, not of churned customers")
        none = m.churn_shares([seg("annual", "yes", "3+", 0, 10, 5, 100)], "plan")
        self.assertEqual(none, {"annual": {"customers": None, "mrr": None}}, "nobody churned: shares are None")

    def test_text_chart(self):
        lines = m.text_chart([("month 1", 1.0), ("month 12", 0.5), ("never", 0.0)], width=10)
        self.assertEqual([ln.count("#") for ln in lines], [10, 5, 0], "100% is `width` characters")
        self.assertIn("50.0%", lines[1])
        self.assertEqual(m.text_chart([]), [])


class OnDataMixin:
    path = DATA

    @classmethod
    def setUpClass(cls):
        cls.rows = read_rows(cls.path)
        cls.con = m.load_db(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.con.close()

    def test_life(self):
        got = run_sql(self.con, m.LIFE_SQL)
        top = max(tenure(r) for r in self.rows)
        plans = sorted({r["plan"] for r in self.rows})
        self.assertEqual([(g["plan"], g["tenure_month"]) for g in got],
                         [(p, n) for p in plans for n in range(1, top + 1)],
                         "one row per plan and month 1 to the longest tenure")
        for g in got:
            mine = [r for r in self.rows if r["plan"] == g["plan"]]
            at_risk = sum(tenure(r) >= g["tenure_month"] for r in mine)
            churned = sum(bool(r["churn_month"]) and tenure(r) == g["tenure_month"] for r in mine)
            self.assertEqual((g["at_risk"], g["churned"]), (at_risk, churned),
                             "%s month %d: at_risk and churned" % (g["plan"], g["tenure_month"]))

    def expected_segments(self):
        out = {}
        for r in self.rows:
            e = out.setdefault((r["plan"], r["onboarded"], size(r)), [0, 0, 0, 0, 0, 0])
            gone = bool(r["churn_month"])
            e[0] += 1
            e[1] += gone
            e[2] += tenure(r)
            e[3] += not gone
            e[4] += 0 if gone else int(r["mrr"])
            e[5] += int(r["mrr"]) if gone else 0
        return out

    def test_segments(self):
        exp = self.expected_segments()
        got = run_sql(self.con, m.SEGMENT_SQL)
        self.assertEqual([(g["plan"], g["onboarded"], g["size"]) for g in got], sorted(exp))
        for g in got:
            self.assertEqual([g["customers"], g["churned"], g["customer_months"], g["active_customers"],
                              g["active_mrr"], g["churned_mrr"]], exp[(g["plan"], g["onboarded"], g["size"])],
                             "segment %s %s %s" % (g["plan"], g["onboarded"], g["size"]))

    def test_insight(self):
        exp = self.expected_segments()
        h = {k: v[1] / v[2] for k, v in exp.items()}
        kept = 0.0
        for (plan, onb, sz), v in exp.items():
            if onb == "no" and (plan, "yes", sz) in h:
                kept += v[4] * max(0.0, h[(plan, "no", sz)] - h[(plan, "yes", sz)])
        segs = run_sql(self.con, m.SEGMENT_SQL)
        onboarding = m.lever(segs, "onboarded", "no", "yes")
        self.assertAlmostEqual(onboarding["mrr_kept"], kept, places=4, msg="MRR kept a month by the onboarding lever")
        self.assertGreater(onboarding["mrr_kept"], m.lever(segs, "size", "1-2", "3+")["mrr_kept"],
                           "the planted answer: onboarding keeps more MRR than fixing small accounts")
        small = m.churn_shares(segs, "size")["1-2"]
        self.assertGreater(small["customers"], small["mrr"],
                           "small accounts are a bigger share of churned customers than of churned MRR")
        life = run_sql(self.con, m.LIFE_SQL)
        mine = [r for r in self.rows if r["plan"] == "monthly"]
        s = 1.0
        for n in (1, 2, 3):
            s *= 1 - sum(bool(r["churn_month"]) and tenure(r) == n for r in mine) / sum(tenure(r) >= n for r in mine)
        self.assertAlmostEqual(dict(m.survival(life, "monthly"))[3], s, places=9, msg="monthly survival after 3 months")


class TestOnData(OnDataMixin, unittest.TestCase):
    pass


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.path = os.path.join(cls.tmp, "customers.csv")
        make_data.write_csv(make_data.build(seed=OTHER_SEED)["customers"], cls.path)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(cls.tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
