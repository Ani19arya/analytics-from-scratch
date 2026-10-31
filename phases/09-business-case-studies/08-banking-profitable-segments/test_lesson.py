"""Tests for case 08: banking, which segments are profitable? Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Every expected number is computed here in plain Python from the CSV rows, never
with SQL and never read from the solution. The checks run on the committed data,
on a second dataset built in memory with another seed, and on tiny hand-made
tables (a changed rate card, a customer with zero activity, a tie at zero
profit, an empty list, a loss-making total).
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
CUSTOMERS = os.path.join(HERE, "data", "customers.csv")
RATES = os.path.join(HERE, "data", "rates.csv")
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


def read_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def run_sql(con, sql):
    body = "\n".join(ln for ln in (sql or "").splitlines() if not ln.strip().startswith("--"))
    if not body.strip():
        raise AssertionError("the query is still a TODO: write it in the exercise file")
    return m.query(con, sql)


def expected_profit(c, r):
    """(revenue, cost_to_serve, charge_off, profit) for one CSV row and a rate dict."""
    rev = (float(c["deposit_balance"]) * r["deposit_margin"] + float(c["loan_balance"]) * r["loan_margin"]
           + float(c["fee_income"]))
    cost = (int(c["branch_visits"]) * r["branch_visit"] + int(c["calls"]) * r["call"]
            + int(c["digital_sessions"]) * r["digital_session"] + r["account_fixed"])
    co = float(c["charge_off"])
    return rev, cost, co, rev - cost - co


def tiny_db(customers, rates):
    """customers: (id, segment, deposit, loan, fees, visits, calls, digital, charge_off); rates: dict."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE customers (customer_id TEXT, segment TEXT, deposit_balance REAL,"
                " loan_balance REAL, fee_income REAL, branch_visits INTEGER, calls INTEGER,"
                " digital_sessions INTEGER, charge_off REAL)")
    con.execute("CREATE TABLE rates (item TEXT, value REAL)")
    con.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", customers)
    con.executemany("INSERT INTO rates VALUES (?, ?)", list(rates.items()))
    return con


RATES_A = {"deposit_margin": 0.02, "loan_margin": 0.05, "branch_visit": 10.0, "call": 5.0,
           "digital_session": 0.5, "account_fixed": 20.0}


def seg(name, customers, revenue, cost, charge_offs):
    return {"segment": name, "customers": customers, "revenue": revenue, "cost_to_serve": cost,
            "charge_offs": charge_offs, "profit": revenue - cost - charge_offs}


class TestHandMade(unittest.TestCase):
    def test_profit_uses_the_rates_table(self):
        con = tiny_db([("C2", "B", 1000.0, 2000.0, 10.0, 2, 1, 10, 50.0),
                       ("C1", "A", 0.0, 0.0, 0.0, 0, 0, 0, 0.0)], RATES_A)
        got = run_sql(con, m.PROFIT_SQL)
        self.assertEqual([g["customer_id"] for g in got], ["C1", "C2"], "one row per customer, ordered by customer_id")
        self.assertEqual((got[0]["revenue"], got[0]["cost_to_serve"], got[0]["profit"]), (0.0, 20.0, -20.0),
                         "a customer with no balances and no activity still costs the fixed 20 a year")
        self.assertEqual((got[1]["revenue"], got[1]["cost_to_serve"], got[1]["charge_off"], got[1]["profit"]),
                         (130.0, 50.0, 50.0, 30.0),
                         "revenue 1000 x 0.02 + 2000 x 0.05 + 10 = 130; cost 2 x 10 + 1 x 5 + 10 x 0.5 + 20 = 50")

    def test_segment_sql_and_rate_change(self):
        rows = [("C1", "A", 1000.0, 0.0, 0.0, 0, 0, 0, 0.0), ("C2", "A", 0.0, 0.0, 0.0, 3, 0, 0, 0.0),
                ("C3", "B", 0.0, 0.0, 100.0, 0, 0, 0, 0.0)]
        got = run_sql(tiny_db(rows, RATES_A), m.SEGMENT_SQL)
        self.assertEqual([(g["segment"], g["customers"], g["profit"], g["profit_per_customer"], g["unprofitable"])
                          for g in got],
                         [("B", 1, 80.0, 80.0, 0), ("A", 2, -50.0, -25.0, 1)],
                         "segments ordered by profit, largest first; unprofitable counts customers below 0")
        cheaper = dict(RATES_A, branch_visit=1.0)
        a = [g for g in run_sql(tiny_db(rows, cheaper), m.SEGMENT_SQL) if g["segment"] == "A"][0]
        self.assertEqual(a["profit"], -23.0, "change the rates table and the profit must change: read it, do not type it in")

    def test_zero_profit_counts_as_profitable(self):
        rows = [("C1", "A", 1000.0, 0.0, 0.0, 0, 0, 0, 0.0)]
        r = dict(RATES_A, account_fixed=20.0)
        got = run_sql(tiny_db(rows, r), m.SEGMENT_SQL)
        self.assertEqual((got[0]["profit"], got[0]["unprofitable"]), (0.0, 0), "profit exactly 0 is not below 0")

    def test_even_allocation_and_flips(self):
        rows = [seg("Branchy", 10, 1000.0, 900.0, 0.0), seg("Digital", 10, 1000.0, 100.0, 0.0),
                seg("Lossy", 10, 100.0, 500.0, 0.0)]
        even = m.even_allocation(rows)
        self.assertEqual({k: round(v, 6) for k, v in even.items()}, {"Branchy": 500.0, "Digital": 500.0, "Lossy": -400.0},
                         "even allocation: total cost 1500 / 30 customers = 50 each, so 500 per segment of 10")
        self.assertEqual(m.flips(rows), [], "no segment changes sign here")
        rows[0] = seg("Branchy", 10, 1000.0, 1200.0, 0.0)
        self.assertEqual(m.flips(rows), ["Branchy"], "Branchy loses money costed by activity but looks profitable split evenly")
        self.assertEqual(m.even_allocation([]), {}, "no segments: empty dict")

    def test_top_share_and_whale(self):
        profits = [50.0, -10.0, 30.0, -20.0, 0.0]
        self.assertAlmostEqual(m.top_share(profits, 0.2), 1.0, msg="top 1 of 5 customers earns 50 of a total of 50")
        self.assertAlmostEqual(m.top_share(profits, 0.4), 1.6, msg="the top two earn 80 of 50: a share above 1 is real")
        self.assertIsNone(m.top_share([], 0.2), "no customers: None")
        self.assertIsNone(m.top_share([-5.0, 2.0], 0.5), "total profit not positive: None")
        w = m.whale_curve(profits)
        self.assertAlmostEqual(w["total"], 50.0)
        self.assertAlmostEqual(w["peak"], 80.0, msg="cumulative 50, 80, 80, 70, 50: the peak is 80")
        self.assertAlmostEqual(w["peak_ratio"], 1.6)
        self.assertEqual(w["unprofitable"], 2, "a profit of exactly 0 is not unprofitable")
        self.assertIsNone(m.whale_curve([-1.0])["peak_ratio"], "total not positive: peak_ratio None")
        self.assertEqual(m.whale_curve([])["peak"], 0)

    def test_text_chart(self):
        self.assertEqual(m.text_chart([]), [])
        lines = m.text_chart([("A", 100.0), ("Bb", -50.0), ("C", 0.0)], width=10)
        self.assertEqual([ln.count("#") for ln in lines], [10, 0, 0])
        self.assertEqual(lines[1].rstrip().endswith("-----"), True, "a negative value draws '-' bars")
        self.assertTrue(lines[1].startswith("Bb "), "each line starts with the label")
        self.assertEqual(m.text_chart([("A", 0.0)], width=10)[0].count("#"), 0, "all zero: no bars")


class OnDataMixin:
    customers_path = CUSTOMERS
    rates_path = RATES

    @classmethod
    def setUpClass(cls):
        cls.customers = read_rows(cls.customers_path)
        cls.rates = {r["item"]: float(r["value"]) for r in read_rows(cls.rates_path)}
        cls.con = m.load_db(cls.customers_path, cls.rates_path)

    def test_profit_sql(self):
        got = {g["customer_id"]: g for g in run_sql(self.con, m.PROFIT_SQL)}
        self.assertEqual(len(got), len(self.customers), "one row per customer")
        for c in self.customers:
            rev, cost, co, profit = expected_profit(c, self.rates)
            g = got[c["customer_id"]]
            self.assertAlmostEqual(g["revenue"], rev, places=1, msg="revenue of %s" % c["customer_id"])
            self.assertAlmostEqual(g["cost_to_serve"], cost, places=1, msg="cost_to_serve of %s" % c["customer_id"])
            self.assertAlmostEqual(g["profit"], profit, places=1, msg="profit of %s" % c["customer_id"])

    def expected_segments(self):
        out = {}
        for c in self.customers:
            rev, cost, co, profit = expected_profit(c, self.rates)
            s = out.setdefault(c["segment"], {"segment": c["segment"], "customers": 0, "revenue": 0.0,
                                              "cost_to_serve": 0.0, "charge_offs": 0.0, "profit": 0.0,
                                              "unprofitable": 0})
            s["customers"] += 1
            s["revenue"] += rev
            s["cost_to_serve"] += cost
            s["charge_offs"] += co
            s["profit"] += profit
            s["unprofitable"] += profit < 0
        return out

    def test_segment_sql(self):
        exp = self.expected_segments()
        got = run_sql(self.con, m.SEGMENT_SQL)
        self.assertEqual([g["segment"] for g in got], sorted(exp, key=lambda k: -exp[k]["profit"]),
                         "one row per segment, ordered by profit, largest first")
        for g in got:
            e = exp[g["segment"]]
            for k in ("revenue", "cost_to_serve", "charge_offs", "profit"):
                self.assertAlmostEqual(g[k], e[k], places=1, msg="%s of %s" % (k, g["segment"]))
            self.assertAlmostEqual(g["profit_per_customer"], e["profit"] / e["customers"], places=1)
            self.assertEqual((g["customers"], g["unprofitable"]), (e["customers"], e["unprofitable"]))

    def test_insight(self):
        exp = self.expected_segments()
        n = sum(e["customers"] for e in exp.values())
        per = sum(e["cost_to_serve"] for e in exp.values()) / n
        expected_flips = sorted(k for k, e in exp.items()
                                if (e["profit"] < 0) != (e["revenue"] - e["charge_offs"] - e["customers"] * per < 0))
        self.assertIn("Retirees", expected_flips, "the planted flip is Retirees")
        segs = run_sql(self.con, m.SEGMENT_SQL)
        self.assertEqual(m.flips(segs), expected_flips)
        even = m.even_allocation(segs)
        for k, e in exp.items():
            self.assertAlmostEqual(even[k], e["revenue"] - e["charge_offs"] - e["customers"] * per, places=0)
        profits = [expected_profit(c, self.rates)[3] for c in self.customers]
        k = int(len(profits) * 0.2)
        self.assertAlmostEqual(m.top_share(profits, 0.2), sum(sorted(profits, reverse=True)[:k]) / sum(profits), places=9)
        positives = sum(p for p in profits if p > 0)
        w = m.whale_curve(profits)
        self.assertAlmostEqual(w["peak"], positives, places=4, msg="the curve peaks after the last profitable customer")
        self.assertAlmostEqual(w["peak_ratio"], positives / sum(profits), places=9)
        self.assertEqual(w["unprofitable"], sum(1 for p in profits if p < 0))


class TestOnData(OnDataMixin, unittest.TestCase):
    pass


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        data = make_data.build(seed=OTHER_SEED)
        cls.customers_path = os.path.join(cls.tmp, "customers.csv")
        cls.rates_path = os.path.join(cls.tmp, "rates.csv")
        make_data.write_csv(data["customers"], make_data.CUSTOMER_FIELDS, cls.customers_path)
        make_data.write_csv(data["rates"], make_data.RATE_FIELDS, cls.rates_path)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
