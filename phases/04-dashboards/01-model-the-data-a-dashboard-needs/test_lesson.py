"""Tests for lesson 01: model the data a dashboard needs.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

"""
import csv
import datetime
import os
import re
import sqlite3
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if os.environ.get("CHECK_SOLUTION") == "1":
    SQL_FILE = os.path.join(HERE, "solution", "solution.sql")
else:
    SQL_FILE = os.path.join(HERE, "exercise.sql")

MODEL = ["dim_date", "dim_product", "dim_region", "fact_sales"]


def cast(value):
    if value == "":
        return None
    for kind in (int, float):
        try:
            return kind(value)
        except ValueError:
            pass
    return value


def read_csv(table):
    with open(os.path.join(HERE, "data", table + ".csv"), newline="") as f:
        return [{k: cast(v) for k, v in row.items()} for row in csv.DictReader(f)]


def load_db():
    con = sqlite3.connect(":memory:")
    rows = read_csv("transactions")
    cols = list(rows[0].keys())
    con.execute("CREATE TABLE transactions (%s)" % ", ".join(cols))
    con.executemany(
        "INSERT INTO transactions VALUES (%s)" % ", ".join("?" * len(cols)),
        [[r[c] for c in cols] for r in rows],
    )
    return con


def load_queries(path):
    queries, name, buf = {}, None, []
    with open(path) as f:
        for line in f:
            m = re.match(r"\s*--\s*query:\s*(\w+)", line)
            if m:
                if name:
                    queries[name] = "".join(buf)
                name, buf = m.group(1), []
            elif name is not None and not line.strip().startswith("--"):
                buf.append(line)
    if name:
        queries[name] = "".join(buf)
    return {k: v.strip().rstrip(";") for k, v in queries.items()}


class TestStarSchema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.con = load_db()
        cls.queries = load_queries(SQL_FILE)
        cls.errors = {}
        for name in MODEL:
            sql = cls.queries.get(name, "")
            if not sql:
                cls.errors[name] = "query '%s' is empty in %s: write it first" % (name, os.path.basename(SQL_FILE))
                continue
            try:
                cls.con.execute("CREATE TABLE %s AS %s" % (name, sql))
            except sqlite3.Error as e:
                cls.errors[name] = "query '%s' failed: %s" % (name, e)
        cls.raw = read_csv("transactions")

    def need(self, *names):
        for name in names:
            if name in self.errors:
                self.fail(self.errors[name])

    def q(self, sql):
        return [tuple(r) for r in self.con.execute(sql).fetchall()]

    def test_dim_date_has_every_calendar_day(self):
        self.need("dim_date")
        rows = self.q("SELECT date_key, date, year, quarter, month, year_month FROM dim_date ORDER BY date_key")
        dates = [r["order_date"] for r in self.raw]
        first = datetime.date.fromisoformat(min(dates))
        last = datetime.date.fromisoformat(max(dates))
        expected = []
        day = first
        while day <= last:
            expected.append((int(day.strftime("%Y%m%d")), day.isoformat(), day.year,
                             (day.month + 2) // 3, day.month, day.strftime("%Y-%m")))
            day += datetime.timedelta(days=1)
        self.assertGreater(len(expected), len(set(dates)), "data should have days with no sales")
        self.assertEqual(len(rows), len(expected),
                         "dim_date needs every day from %s to %s, not only days with sales" % (first, last))
        self.assertEqual(rows, expected)

    def test_dim_product_one_row_per_product(self):
        self.need("dim_product")
        rows = self.q("SELECT product_key, product, category FROM dim_product")
        expected = {(r["product"], r["category"]) for r in self.raw}
        self.assertEqual(len(rows), len(expected), "one row per product")
        self.assertEqual(len({r[0] for r in rows}), len(rows), "product_key must be unique")
        self.assertTrue(all(isinstance(r[0], int) for r in rows), "product_key must be an integer")
        self.assertEqual({(r[1], r[2]) for r in rows}, expected)

    def test_dim_region_one_row_per_region(self):
        self.need("dim_region")
        rows = self.q("SELECT region_key, region, region_manager FROM dim_region")
        expected = {(r["region"], r["region_manager"]) for r in self.raw}
        self.assertEqual(len(rows), len(expected), "one row per region")
        self.assertEqual(len({r[0] for r in rows}), len(rows), "region_key must be unique")
        self.assertTrue(all(isinstance(r[0], int) for r in rows), "region_key must be an integer")
        self.assertEqual({(r[1], r[2]) for r in rows}, expected)

    def test_fact_grain_is_one_row_per_order_line(self):
        self.need("fact_sales")
        rows = self.q("SELECT order_id, line_no FROM fact_sales")
        self.assertEqual(len(rows), len(self.raw), "fact_sales must have one row per raw order line")
        self.assertEqual(len(set(rows)), len(rows), "(order_id, line_no) must be unique in fact_sales")

    def test_fact_keys_all_resolve(self):
        self.need(*MODEL)
        orphans = self.q("""
            SELECT COUNT(*) FROM fact_sales f
            LEFT JOIN dim_date d ON d.date_key = f.date_key
            LEFT JOIN dim_product p ON p.product_key = f.product_key
            LEFT JOIN dim_region r ON r.region_key = f.region_key
            WHERE d.date_key IS NULL OR p.product_key IS NULL OR r.region_key IS NULL""")[0][0]
        self.assertEqual(orphans, 0, "every fact row must join to every dimension")

    def test_totals_match_raw_data(self):
        self.need(*MODEL)
        qty, revenue = self.q("SELECT SUM(quantity), SUM(revenue) FROM fact_sales")[0]
        self.assertEqual(qty, sum(r["quantity"] for r in self.raw))
        raw_rev = sum(round(r["quantity"] * r["unit_price"], 2) for r in self.raw)
        self.assertAlmostEqual(revenue, raw_rev, delta=0.01)
        by_region = dict(self.q("""SELECT r.region, ROUND(SUM(f.revenue), 2) FROM fact_sales f
                                   JOIN dim_region r ON r.region_key = f.region_key GROUP BY r.region"""))
        for region in {r["region"] for r in self.raw}:
            want = sum(round(r["quantity"] * r["unit_price"], 2) for r in self.raw if r["region"] == region)
            self.assertAlmostEqual(by_region.get(region, 0), want, delta=0.01, msg="revenue for %s" % region)

    def test_revenue_by_category_month(self):
        self.need(*MODEL)
        sql = self.queries.get("revenue_by_category_month", "")
        if not sql:
            self.fail("query 'revenue_by_category_month' is empty: write it first")
        self.assertNotIn("transactions", sql.lower(), "build this visual from the star schema, not the raw table")
        totals = {}
        for r in self.raw:
            key = (r["order_date"][:7], r["category"])
            totals[key] = totals.get(key, 0) + round(r["quantity"] * r["unit_price"], 2)
        expected = [(k[0], k[1], round(v, 2)) for k, v in sorted(totals.items())]
        actual = self.q(sql)
        self.assertEqual(len(actual), len(expected), "one row per month and category")
        for a, e in zip(actual, expected):
            self.assertEqual(a[:2], e[:2])
            self.assertAlmostEqual(a[2], e[2], delta=0.011, msg="row %r, expected %r" % (a, e))


if __name__ == "__main__":
    unittest.main()
