"""Tests for case 06: retail, what to restock. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Every expected number is computed here in plain Python from the CSV rows, never
with SQL and never read from the solution. The checks run on the committed data,
on a second dataset built in memory with another seed, and on tiny hand-made
tables (a product with no sales rows, a product never in stock, zero demand,
an order that lands exactly on a whole unit, an all-zero chart).
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
PRODUCTS = os.path.join(HERE, "data", "products.csv")
SALES = os.path.join(HERE, "data", "weekly_sales.csv")
OTHER_SEED = 9
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


def tiny_db(products, sales):
    """products: (sku, category, cost, price, on_hand, lead); sales: (week_start, sku, units, in_stock)."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE products (sku TEXT, name TEXT, category TEXT, unit_cost REAL,"
                " unit_price REAL, on_hand INTEGER, lead_time_weeks INTEGER)")
    con.execute("CREATE TABLE weekly_sales (week_start TEXT, sku TEXT, units_sold INTEGER, in_stock INTEGER)")
    for sku, cat, cost, price, on_hand, lead in products:
        con.execute("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", (sku, sku, cat, cost, price, on_hand, lead))
    con.executemany("INSERT INTO weekly_sales VALUES (?, ?, ?, ?)", sales)
    return con


def sku_row(sku="A", on_hand=0, lead=1, weeks=4, in_stock_weeks=4, units_in_stock=40, units_total=40,
            cost=2.0, price=5.0, category="tools"):
    return {"sku": sku, "category": category, "unit_cost": cost, "unit_price": price, "on_hand": on_hand,
            "lead_time_weeks": lead, "weeks": weeks, "in_stock_weeks": in_stock_weeks,
            "units_in_stock": units_in_stock, "units_total": units_total}


class TestHandMade(unittest.TestCase):
    def test_product_without_sales_rows_is_kept(self):
        con = tiny_db([("A", "tools", 2.0, 5.0, 10, 1), ("B", "paint", 1.0, 3.0, 7, 2)],
                      [("2026-08-03", "A", 4, 1), ("2026-08-10", "A", 1, 0)])
        got = run_sql(con, m.SKU_SQL)
        self.assertEqual([g["sku"] for g in got], ["A", "B"],
                         "every product appears, even one with no sales rows: start from products and LEFT JOIN")
        b = got[1]
        self.assertEqual([b["weeks"], b["in_stock_weeks"], b["units_in_stock"], b["units_total"]], [0, 0, 0, 0],
                         "a product with no sales rows has counts 0, not NULL: use COALESCE")
        a = got[0]
        self.assertEqual([a["weeks"], a["in_stock_weeks"], a["units_in_stock"], a["units_total"]], [2, 1, 4, 5],
                         "units_in_stock counts only units sold in weeks with in_stock = 1")

    def test_weekly_counts_out_of_stock(self):
        con = tiny_db([("A", "tools", 2.0, 5.0, 10, 1), ("B", "paint", 1.0, 2.5, 7, 2)],
                      [("2026-08-03", "A", 4, 1), ("2026-08-03", "B", 2, 0), ("2026-08-10", "A", 0, 1)])
        got = run_sql(con, m.WEEKLY_SQL)
        self.assertEqual([(g["week_start"], g["units"], g["revenue"], g["skus_out"]) for g in got],
                         [("2026-08-03", 6, 25.0, 1), ("2026-08-10", 0, 0.0, 0)],
                         "a week with nothing out of stock shows skus_out 0, and revenue is units x unit_price")

    def test_demand_ignores_out_of_stock_weeks(self):
        r = sku_row(weeks=4, in_stock_weeks=2, units_in_stock=20, units_total=24)
        self.assertAlmostEqual(m.demand_per_week(r), 10.0,
                               msg="demand = units in in-stock weeks / in-stock weeks (20 / 2), not 24 / 4")
        self.assertIsNone(m.demand_per_week(sku_row(in_stock_weeks=0, units_in_stock=0, units_total=0)),
                          "never in stock: demand is unknown, return None")

    def test_plan_rules(self):
        rows = [
            sku_row("A", on_hand=10, lead=1, weeks=4, in_stock_weeks=2, units_in_stock=20, units_total=24),
            sku_row("B", on_hand=25, lead=1, weeks=4, in_stock_weeks=4, units_in_stock=20, units_total=20),
            sku_row("C", on_hand=30, lead=2, weeks=4, in_stock_weeks=4, units_in_stock=0, units_total=0),
            sku_row("D", on_hand=0, lead=2, weeks=0, in_stock_weeks=0, units_in_stock=0, units_total=0),
            sku_row("E", on_hand=100, lead=1, weeks=4, in_stock_weeks=4, units_in_stock=20, units_total=20),
        ]
        p = {r["sku"]: r for r in m.plan(rows)}
        self.assertEqual([r["sku"] for r in m.plan(rows)], list("ABCDE"), "keep the order of the input rows")
        a = p["A"]
        self.assertEqual((a["action"], a["order_qty"]), ("restock", 40),
                         "A: demand 10 a week x (1 + 4) weeks = 50, minus 10 on hand = order 40")
        self.assertAlmostEqual(a["order_cost"], 80.0)
        self.assertAlmostEqual(a["lost_margin"], (10 * 2 - 4) * 3.0,
                               msg="lost margin: 2 out-of-stock weeks x 10 wanted, minus 4 sold, x (price - cost)")
        self.assertAlmostEqual(a["cover_weeks"], 1.0)
        self.assertEqual((p["B"]["action"], p["B"]["order_qty"]), ("hold", 0),
                         "B: demand 5 x 5 weeks = 25 equals the 25 on hand exactly: order 0, not 1")
        c = p["C"]
        self.assertEqual(c["action"], "overstock", "C: in stock all along, sold nothing: all 30 units are excess")
        self.assertIsNone(c["cover_weeks"], "zero demand: cover is None, not a division by zero")
        self.assertAlmostEqual(c["excess_value"], 60.0)
        self.assertEqual(p["D"]["action"], "review", "D: never in stock, demand unknown: review, do not guess")
        e = p["E"]
        self.assertEqual(e["action"], "overstock")
        self.assertAlmostEqual(e["excess_units"], 40.0, msg="E: 100 on hand - 5 a week x 12 weeks = 40 excess")

    def test_order_rounds_up(self):
        p = m.plan([sku_row(on_hand=0, lead=1, weeks=3, in_stock_weeks=3, units_in_stock=10, units_total=10)])[0]
        self.assertEqual(p["order_qty"], 17, "demand 3.33 x 5 weeks = 16.7 units: round up to 17 whole units")

    def test_summarise(self):
        s = m.summarise([])
        self.assertEqual({k: s[k] for k in ("restock", "overstock", "hold", "review")},
                         {"restock": 0, "overstock": 0, "hold": 0, "review": 0},
                         "all four action counts are present, even when 0")
        self.assertEqual((s["order_cost"], s["cash_tied_up"], s["lost_margin"]), (0, 0, 0))

    def test_text_chart(self):
        self.assertEqual(m.text_chart([]), [])
        lines = m.text_chart([("paint", 50.0), ("tools", 100.0), ("garden", 0.0)], width=10)
        self.assertEqual([ln.count("#") for ln in lines], [5, 10, 0], "the largest value gets `width` characters")
        self.assertTrue(lines[2].startswith("garden "), "each line starts with the label")
        self.assertEqual(len(set(ln.index(" ", 6) for ln in lines)), 1, "labels are padded to the same width")
        self.assertEqual(m.text_chart([("x", 0.0)], width=10)[0].count("#"), 0, "all values 0: no bars")


class OnDataMixin:
    products_path = PRODUCTS
    sales_path = SALES

    @classmethod
    def setUpClass(cls):
        cls.products = read_rows(cls.products_path)
        cls.sales = read_rows(cls.sales_path)
        cls.con = m.load_db(cls.products_path, cls.sales_path)

    def expected_skus(self):
        agg = {p["sku"]: [0, 0, 0, 0] for p in self.products}
        for s in self.sales:
            a = agg[s["sku"]]
            a[0] += 1
            a[1] += int(s["in_stock"])
            a[2] += int(s["units_sold"]) if s["in_stock"] == "1" else 0
            a[3] += int(s["units_sold"])
        return agg

    def test_sku_sql(self):
        exp = self.expected_skus()
        got = run_sql(self.con, m.SKU_SQL)
        self.assertEqual([g["sku"] for g in got], sorted(exp), "one row per product, ordered by sku")
        for g in got:
            self.assertEqual([g["weeks"], g["in_stock_weeks"], g["units_in_stock"], g["units_total"]], exp[g["sku"]],
                             "counts for %s" % g["sku"])

    def test_weekly_sql(self):
        price = {p["sku"]: float(p["unit_price"]) for p in self.products}
        exp = {}
        for s in self.sales:
            e = exp.setdefault(s["week_start"], [0, 0.0, 0])
            e[0] += int(s["units_sold"])
            e[1] += int(s["units_sold"]) * price[s["sku"]]
            e[2] += s["in_stock"] == "0"
        got = run_sql(self.con, m.WEEKLY_SQL)
        self.assertEqual([g["week_start"] for g in got], sorted(exp), "one row per week, in order")
        for g in got:
            u, rev, out = exp[g["week_start"]]
            self.assertEqual((g["units"], g["skus_out"]), (u, out), "week %s" % g["week_start"])
            self.assertAlmostEqual(g["revenue"], rev, delta=0.006)

    def test_plan_and_summary(self):
        exp = self.expected_skus()
        prod = {p["sku"]: p for p in self.products}
        counts = {"restock": 0, "overstock": 0, "hold": 0, "review": 0}
        order_cost = tied = lost = 0.0
        expected_actions = {}
        for sku, (weeks, isw, uis, ut) in exp.items():
            p = prod[sku]
            cost, price, on_hand, lead = float(p["unit_cost"]), float(p["unit_price"]), int(p["on_hand"]), int(p["lead_time_weeks"])
            if isw == 0:
                action = "review"
            else:
                d = uis / isw
                need = d * (lead + 4) - on_hand
                qty = math.ceil(round(need, 9)) if need > 0 else 0
                excess = max(0.0, on_hand - 12 * d)
                order_cost += qty * cost
                tied += excess * cost
                lost += max(0.0, d * (weeks - isw) - (ut - uis)) * (price - cost)
                action = "restock" if qty > 0 else ("overstock" if excess > 0 else "hold")
            counts[action] += 1
            expected_actions[sku] = action
        got_plan = m.plan(run_sql(self.con, m.SKU_SQL))
        self.assertEqual({r["sku"]: r["action"] for r in got_plan}, expected_actions,
                         "the action per SKU does not match the rules in the plan() docstring")
        s = m.summarise(got_plan)
        self.assertEqual({k: s[k] for k in counts}, counts)
        self.assertAlmostEqual(s["order_cost"], order_cost, places=4, msg="total cash the restock needs")
        self.assertAlmostEqual(s["cash_tied_up"], tied, places=4, msg="total value of stock above 12 weeks of cover")
        self.assertAlmostEqual(s["lost_margin"], lost, places=4, msg="total margin lost in out-of-stock weeks")


class TestOnData(OnDataMixin, unittest.TestCase):
    pass


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        data = make_data.build(seed=OTHER_SEED)
        cls.products_path = os.path.join(cls.tmp, "products.csv")
        cls.sales_path = os.path.join(cls.tmp, "weekly_sales.csv")
        make_data.write_csv(data["products"], make_data.PRODUCT_FIELDS, cls.products_path)
        make_data.write_csv(data["weekly_sales"], make_data.SALES_FIELDS, cls.sales_path)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
