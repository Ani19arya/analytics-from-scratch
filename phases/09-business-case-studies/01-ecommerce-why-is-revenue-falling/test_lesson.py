"""Tests for case 01: e-commerce revenue. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Every expected number is computed here in plain Python from the CSV rows, never
with SQL and never read from the solution. The checks run on the committed data,
on a second dataset built in memory with another seed, and on tiny hand-made
tables (a channel with no orders, a new channel, no change, a zero).
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
OTHER_SEED = 5
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")

spec = importlib.util.spec_from_file_location("lesson_module", TARGET)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sys.path.insert(0, HERE)
import make_data  # noqa: E402


def read_rows(folder, name):
    with open(os.path.join(folder, name), newline="") as f:
        return list(csv.DictReader(f))


def quarter(d):
    return "Q2" if d < "2026-07-01" else "Q3"


def run_sql(con, sql):
    body = "\n".join(ln for ln in (sql or "").splitlines() if not ln.strip().startswith("--"))
    if not body.strip():
        raise AssertionError("the query is still a TODO: write it in the exercise file")
    return m.query(con, sql)


def tiny_db(sessions, orders):
    """sessions: (date, channel, n). orders: (date, channel, revenue)."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE sessions (date TEXT, channel TEXT, sessions INTEGER)")
    con.execute("CREATE TABLE orders (order_id TEXT, order_date TEXT, channel TEXT, items INTEGER, revenue INTEGER)")
    con.executemany("INSERT INTO sessions VALUES (?, ?, ?)", sessions)
    con.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
                    [("X%d" % i, d, c, 1, r) for i, (d, c, r) in enumerate(orders)])
    return con


def row(q, ch, s, o, r):
    return {"quarter": q, "channel": ch, "sessions": s, "orders": o, "revenue": r}


class TestHandMade(unittest.TestCase):
    def test_sql_no_fan_out_and_zero_orders(self):
        con = tiny_db(
            [("2026-06-30", "search", 100), ("2026-06-29", "search", 100), ("2026-07-01", "search", 50),
             ("2026-07-01", "social", 40)],
            [("2026-06-30", "search", 500), ("2026-06-30", "search", 300), ("2026-07-01", "search", 200)])
        got = [(r["quarter"], r["sessions"], r["orders"], r["revenue"]) for r in run_sql(con, m.QUARTER_SQL)]
        self.assertEqual(got, [("Q2", 200, 2, 800), ("Q3", 90, 1, 200)],
                         "30 June is Q2 and 1 July is Q3; sessions must not be multiplied by the number of orders")
        got = [(r["quarter"], r["channel"], r["sessions"], r["orders"], r["revenue"]) for r in run_sql(con, m.CHANNEL_SQL)]
        self.assertEqual(got, [("Q2", "search", 200, 2, 800), ("Q3", "search", 50, 1, 200), ("Q3", "social", 40, 0, 0)],
                         "a channel with sessions but no orders shows 0 orders and 0 revenue, not NULL and not missing")

    def test_log_mean(self):
        self.assertEqual(m.log_mean(5.0, 5.0), 5.0, "equal values: the log mean is the value itself")
        self.assertAlmostEqual(m.log_mean(1.0, math.e), (math.e - 1) / 1.0)

    def test_lmdi_sums_exactly(self):
        before = {"sessions": 1000, "orders": 30, "revenue": 60000}
        after = {"sessions": 1100, "orders": 27, "revenue": 56700}
        e = m.lmdi(before, after)
        self.assertAlmostEqual(sum(e.values()), after["revenue"] - before["revenue"], places=6,
                               msg="the three effects must add up exactly to the revenue change")
        w = (56700 - 60000) / math.log(56700 / 60000)
        self.assertAlmostEqual(e["sessions"], w * math.log(1.1), places=6)
        self.assertAlmostEqual(e["basket"], w * math.log((56700 / 27) / 2000), places=6)

    def test_lmdi_no_change_and_zero(self):
        same = {"sessions": 10, "orders": 2, "revenue": 300}
        self.assertEqual({k: round(v, 9) for k, v in m.lmdi(same, dict(same)).items()},
                         {"sessions": 0.0, "conversion": 0.0, "basket": 0.0}, "no change: every effect is 0")
        self.assertIsNone(m.lmdi(same, {"sessions": 10, "orders": 0, "revenue": 0}),
                          "a quarter with no orders has no conversion or basket to compare: None")

    def test_mix_and_rate_pure_mix(self):
        rows = [row("Q2", "a", 50, 5, 500), row("Q2", "b", 50, 1, 100),
                row("Q3", "a", 20, 2, 200), row("Q3", "b", 80, 2, 160)]
        r = m.mix_and_rate(rows)
        self.assertAlmostEqual(r["rate"], 0.0, msg="RPS within each channel did not change, so the rate effect is 0")
        self.assertAlmostEqual(r["mix"], r["rps_after"] - r["rps_before"],
                               msg="all of the RPS change is mix here")
        self.assertAlmostEqual(r["rps_before"], 6.0)
        self.assertAlmostEqual(r["rps_after"], 3.6)

    def test_mix_and_rate_new_channel_and_sum(self):
        rows = [row("Q2", "a", 100, 4, 400), row("Q3", "a", 60, 3, 360), row("Q3", "c", 40, 0, 0)]
        r = m.mix_and_rate(rows)
        self.assertAlmostEqual(r["mix"] + r["rate"], r["rps_after"] - r["rps_before"],
                               msg="mix + rate must equal the total change in RPS")
        self.assertAlmostEqual(r["by_channel"]["c"]["rate"], 0.0, msg="a channel new in Q3 has no rate effect, only mix")
        self.assertAlmostEqual(r["by_channel"]["a"]["rate"], (6.0 - 4.0) * (1.0 + 0.6) / 2)
        self.assertIsNone(m.mix_and_rate([row("Q2", "a", 10, 1, 10)]), "no Q3 sessions: None")

    def test_waterfall(self):
        self.assertEqual(m.waterfall([]), [])
        lines = m.waterfall([("start", 1000), ("up", 500), ("down", -250), ("end", 1250)], width=10)
        self.assertEqual([ln.count("#") for ln in lines], [8, 0, 0, 10], "totals use # scaled to the largest value")
        self.assertEqual(lines[1].count("+") - 1, 4, "a +500 change gets 4 '+' marks when 1,250 gets 10 (the 1 is the sign)")
        self.assertEqual(lines[2].count("-") - 1, 2, "a -250 change gets 2 '-' marks (plus the minus sign)")
        self.assertIn("1,250", lines[3], "values use thousands commas")
        self.assertIn("+500", lines[1], "changes show their sign")


class OnDataMixin:
    folder = DATA

    @classmethod
    def setUpClass(cls):
        cls.sessions = read_rows(cls.folder, "sessions.csv")
        cls.orders = read_rows(cls.folder, "orders.csv")
        cls.con = m.load_db(cls.folder)

    @classmethod
    def tearDownClass(cls):
        cls.con.close()

    def expected_channels(self):
        out = {}
        for r in self.sessions:
            e = out.setdefault((quarter(r["date"]), r["channel"]), [0, 0, 0])
            e[0] += int(r["sessions"])
        for r in self.orders:
            e = out[(quarter(r["order_date"]), r["channel"])]
            e[1] += 1
            e[2] += int(r["revenue"])
        return out

    def test_quarters(self):
        exp = {}
        for (q, _), (s, o, r) in self.expected_channels().items():
            e = exp.setdefault(q, [0, 0, 0])
            e[0] += s
            e[1] += o
            e[2] += r
        got = run_sql(self.con, m.QUARTER_SQL)
        self.assertEqual([g["quarter"] for g in got], ["Q2", "Q3"])
        for g in got:
            self.assertEqual([g["sessions"], g["orders"], g["revenue"]], exp[g["quarter"]],
                             "%s: sessions, orders and revenue; check for a join that repeats rows" % g["quarter"])

    def test_channels(self):
        exp = self.expected_channels()
        got = run_sql(self.con, m.CHANNEL_SQL)
        self.assertEqual([(g["quarter"], g["channel"]) for g in got], sorted(exp), "one row per quarter and channel, in order")
        for g in got:
            self.assertEqual([g["sessions"], g["orders"], g["revenue"]], exp[(g["quarter"], g["channel"])])

    def test_insight(self):
        exp = self.expected_channels()
        tot = {}
        for (q, _), v in exp.items():
            t = tot.setdefault(q, [0, 0, 0])
            for i in range(3):
                t[i] += v[i]
        q2, q3 = tot["Q2"], tot["Q3"]
        w = (q3[2] - q2[2]) / (math.log(q3[2]) - math.log(q2[2]))
        e = m.lmdi(m.query(self.con, m.QUARTER_SQL)[0], m.query(self.con, m.QUARTER_SQL)[1])
        self.assertAlmostEqual(e["sessions"], w * math.log(q3[0] / q2[0]), places=4)
        self.assertAlmostEqual(e["conversion"], w * math.log((q3[1] / q3[0]) / (q2[1] / q2[0])), places=4)
        self.assertAlmostEqual(sum(e.values()), q3[2] - q2[2], places=4)
        mix = rate = 0.0
        for ch in {c for _, c in exp}:
            sb, sa = exp[("Q2", ch)][0] / q2[0], exp[("Q3", ch)][0] / q3[0]
            rb, ra = exp[("Q2", ch)][2] / exp[("Q2", ch)][0], exp[("Q3", ch)][2] / exp[("Q3", ch)][0]
            mix += (sa - sb) * (rb + ra) / 2
            rate += (ra - rb) * (sb + sa) / 2
        r = m.mix_and_rate(run_sql(self.con, m.CHANNEL_SQL))
        self.assertAlmostEqual(r["mix"], mix, places=6, msg="mix effect on revenue per session")
        self.assertAlmostEqual(r["rate"], rate, places=6, msg="rate effect on revenue per session")
        self.assertLess(r["mix"], 0, "the planted cause: the channel mix moved toward low-value social traffic")
        self.assertGreater(abs(r["mix"]), 3 * abs(r["rate"]), "mix, not within-channel performance, explains the drop")


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
