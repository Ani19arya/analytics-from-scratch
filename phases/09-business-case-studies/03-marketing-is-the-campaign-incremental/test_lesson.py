"""Tests for case 03: is the campaign incremental? Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Every expected number is computed here in plain Python from the CSV rows, never
with SQL and never read from the solution. The checks run on the committed data,
on a second dataset built in memory with another seed, and on tiny hand-made
tables (a group with no orders, the date boundary, no lift, an empty holdout).
"""
import csv
import importlib.util
import math
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OTHER_SEED = 4
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")

spec = importlib.util.spec_from_file_location("lesson_module", TARGET)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sys.path.insert(0, HERE)
import make_data  # noqa: E402

NUM = ("orders", "code_orders", "revenue", "code_revenue")


def read_rows(folder, name):
    with open(os.path.join(folder, name), newline="") as f:
        return list(csv.DictReader(f))


def run_sql(con, sql):
    body = "\n".join(ln for ln in (sql or "").splitlines() if not ln.strip().startswith("--"))
    if not body.strip():
        raise AssertionError("the query is still a TODO: write it in the exercise file")
    return m.query(con, sql)


def tiny_db(audience, daily):
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE audience (segment TEXT, grp TEXT, customers INTEGER)")
    con.execute("CREATE TABLE daily (date TEXT, segment TEXT, grp TEXT, orders INTEGER, code_orders INTEGER,"
                " revenue INTEGER, code_revenue INTEGER)")
    con.executemany("INSERT INTO audience VALUES (?, ?, ?)", audience)
    con.executemany("INSERT INTO daily VALUES (?, ?, ?, ?, ?, ?, ?)", daily)
    return con


def grp(seg, g, n, orders, code=0, rev=0, code_rev=0, period="campaign"):
    return {"period": period, "segment": seg, "grp": g, "customers": n, "orders": orders,
            "code_orders": code, "revenue": rev, "code_revenue": code_rev}


class TestHandMade(unittest.TestCase):
    def test_sql_boundary_and_missing_group(self):
        con = tiny_db([("lapsed", "campaign", 100), ("lapsed", "holdout", 10)],
                      [("2026-08-31", "lapsed", "campaign", 2, 0, 200, 0),
                       ("2026-09-01", "lapsed", "campaign", 5, 3, 450, 255)])
        got = [(r["period"], r["grp"], r["customers"], r["orders"], r["code_orders"], r["revenue"], r["code_revenue"])
               for r in run_sql(con, m.GROUP_SQL)]
        self.assertEqual(got, [("campaign", "campaign", 100, 5, 3, 450, 255), ("campaign", "holdout", 10, 0, 0, 0, 0),
                               ("pre", "campaign", 100, 2, 0, 200, 0), ("pre", "holdout", 10, 0, 0, 0, 0)],
                         "1 September is the first campaign day; a group with no orders still appears, with 0s")

    def test_lift_simple(self):
        rows = [grp("a", "campaign", 1000, 60, 40, 6000, 3400), grp("a", "holdout", 100, 4, 0, 400, 0)]
        r = m.lift(rows, "a")
        self.assertAlmostEqual(r["incremental"], (0.06 - 0.04) * 1000,
                               msg="incremental = (rate campaign - rate holdout) x campaign customers")
        se = 1000 * math.sqrt(60 / 1000 ** 2 + 4 / 100 ** 2)
        self.assertAlmostEqual(r["se"], se)
        self.assertAlmostEqual(r["low"], 20 - 1.96 * se)
        self.assertAlmostEqual(r["incremental_revenue"], (6.0 - 4.0) * 1000)
        self.assertEqual(r["attributed"], 40, "attributed sales are the campaign group's code orders")

    def test_lift_none_and_no_effect(self):
        self.assertIsNone(m.lift([grp("a", "campaign", 100, 5)], "a"), "no holdout group: cannot measure")
        self.assertIsNone(m.lift([grp("a", "campaign", 100, 5), grp("a", "holdout", 0, 0)], "a"),
                          "a holdout of 0 customers: None, not a division by zero")
        same = m.lift([grp("a", "campaign", 1000, 50, 30), grp("a", "holdout", 100, 5)], "a")
        self.assertAlmostEqual(same["incremental"], 0.0,
                               msg="same rate in both groups: 0 incremental, even with 30 code orders")
        self.assertIsNone(m.lift([grp("a", "campaign", 100, 5, period="pre"), grp("a", "holdout", 10, 1, period="pre")], "a"),
                          "only the requested period counts")

    def test_total(self):
        rows = [grp("a", "campaign", 1000, 60, 40), grp("a", "holdout", 100, 4),
                grp("b", "campaign", 500, 10, 5), grp("b", "holdout", 50, 1)]
        t = m.total_lift(rows)
        a, b = m.lift(rows, "a"), m.lift(rows, "b")
        self.assertAlmostEqual(t["incremental"], a["incremental"] + b["incremental"])
        self.assertAlmostEqual(t["se"], math.sqrt(a["se"] ** 2 + b["se"] ** 2),
                               msg="independent segments: add variances, not standard errors")
        self.assertEqual(t["attributed"], 45)

    def test_profit(self):
        rows = [grp("a", "campaign", 100, 10, 10, 850, 850), grp("a", "holdout", 100, 10, 0, 1000, 0)]
        self.assertAlmostEqual(m.campaign_profit(rows, "a", 0.40, 0.15), (0.4 * 850 - 0.6 * 150) - 0.4 * 1000,
                               msg="same orders, all discounted: the campaign only gave away margin")
        self.assertIsNone(m.campaign_profit(rows[:1], "a", 0.4, 0.15))

    def test_text_chart(self):
        lifts = [{"segment": "x", "attributed": 100, "incremental": 50.4}, {"segment": "y", "attributed": 20, "incremental": -5}]
        lines = m.text_chart(lifts, width=10)
        self.assertEqual(len(lines), 4, "two lines per segment")
        self.assertEqual([ln.count("#") for ln in lines], [10, 5, 2, 0], "a negative incremental has no bar")
        self.assertTrue(lines[0].startswith("x"), "the first line of a segment starts with its name")
        self.assertIn("50", lines[1])


class OnDataMixin:
    folder = DATA

    @classmethod
    def setUpClass(cls):
        cls.audience = read_rows(cls.folder, "audience.csv")
        cls.daily = read_rows(cls.folder, "daily.csv")
        cls.con = m.load_db(cls.folder)

    @classmethod
    def tearDownClass(cls):
        cls.con.close()

    def expected(self):
        out = {}
        for a in self.audience:
            for p in ("campaign", "pre"):
                out[(p, a["segment"], a["grp"])] = [int(a["customers"]), 0, 0, 0, 0]
        for r in self.daily:
            p = "campaign" if r["date"] >= "2026-09-01" else "pre"
            e = out[(p, r["segment"], r["grp"])]
            for i, k in enumerate(NUM):
                e[i + 1] += int(r[k])
        return out

    def test_groups(self):
        exp = self.expected()
        got = run_sql(self.con, m.GROUP_SQL)
        self.assertEqual([(g["period"], g["segment"], g["grp"]) for g in got], sorted(exp))
        for g in got:
            self.assertEqual([g["customers"]] + [g[k] for k in NUM], exp[(g["period"], g["segment"], g["grp"])],
                             "%s %s %s" % (g["period"], g["segment"], g["grp"]))

    def test_insight(self):
        exp = self.expected()
        rows = run_sql(self.con, m.GROUP_SQL)
        total = attributed = var = 0.0
        for seg in sorted({a["segment"] for a in self.audience}):
            nc, oc = exp[("campaign", seg, "campaign")][:2]
            nh, oh = exp[("campaign", seg, "holdout")][:2]
            inc = (oc / nc - oh / nh) * nc
            r = m.lift(rows, seg)
            self.assertAlmostEqual(r["incremental"], inc, places=6, msg="incremental orders for %s" % seg)
            total += inc
            var += nc * nc * (oc / nc ** 2 + oh / nh ** 2)
            attributed += exp[("campaign", seg, "campaign")][2]
        t = m.total_lift(rows)
        self.assertAlmostEqual(t["incremental"], total, places=6)
        self.assertAlmostEqual(t["se"], math.sqrt(var), places=6)
        self.assertEqual(t["attributed"], attributed)
        self.assertLess(t["incremental"], 0.6 * t["attributed"],
                        "the planted answer: most credited sales would have happened anyway")
        lapsed, loyal = m.lift(rows, "lapsed"), m.lift(rows, "loyal")
        self.assertGreater(lapsed["incremental"] / lapsed["attributed"], loyal["incremental"] / loyal["attributed"],
                           "lapsed customers have the highest share of real orders among credited ones")


class TestOnData(OnDataMixin, unittest.TestCase):
    pass


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.folder = cls.tmp
        make_data.write_all(make_data.build(seed=OTHER_SEED), cls.tmp)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(cls.tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
