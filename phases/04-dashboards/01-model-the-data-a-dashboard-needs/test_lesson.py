"""Tests for lesson 01: model the data a dashboard needs.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

Every expected answer is computed here with plain Python loops over the raw
rows, never read from the solution. The same checks run on three datasets:
the committed CSV, a second dataset built in memory with another seed, and a
tiny hand-made table with a gap day, a zero quantity and a tie.
"""
import csv
import datetime
import importlib.util
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
FACT_COLUMNS = {"order_id", "line_no", "date_key", "product_key", "region_key", "quantity", "revenue"}
DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
SECOND_SEED = 4017


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


def rows_from_build(seed):
    spec = importlib.util.spec_from_file_location("make_data", os.path.join(HERE, "make_data.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return [{k: cast(str(v)) for k, v in r.items()} for r in module.build(seed=seed)["transactions"]]


def load_db(raw):
    con = sqlite3.connect(":memory:")
    cols = ["order_id", "line_no", "order_date", "product", "category", "unit_price",
            "region", "region_manager", "quantity"]
    con.execute("CREATE TABLE transactions (%s)" % ", ".join(cols))
    con.executemany(
        "INSERT INTO transactions VALUES (%s)" % ", ".join("?" * len(cols)),
        [[r[c] for c in cols] for r in raw],
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


def line_revenue(r):
    return round(r["quantity"] * r["unit_price"], 2)


def calendar(raw):
    dates = [r["order_date"] for r in raw]
    day = datetime.date.fromisoformat(min(dates))
    last = datetime.date.fromisoformat(max(dates))
    while day <= last:
        yield day
        day += datetime.timedelta(days=1)


class StarChecks:
    """The checks. Subclasses set cls.raw before setUpClass runs."""

    raw = None

    @classmethod
    def setUpClass(cls):
        cls.con = load_db(cls.raw)
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

    def need(self, *names):
        for name in names:
            if name in self.errors:
                self.fail(self.errors[name])

    def q(self, sql):
        return [tuple(r) for r in self.con.execute(sql).fetchall()]

    def run_named(self, name):
        sql = self.queries.get(name, "")
        if not sql:
            self.fail("query '%s' is empty in %s: write it first" % (name, os.path.basename(SQL_FILE)))
        self.assertNotIn("transactions", sql.lower(), "build '%s' from the star schema, not the raw table" % name)
        return self.q(sql)

    def assertRowsClose(self, actual, expected, what):
        self.assertEqual(len(actual), len(expected), "%s: got %d rows, expected %d" % (what, len(actual), len(expected)))
        for a, e in zip(actual, expected):
            self.assertEqual(len(a), len(e), "%s: row %r should have the columns of %r" % (what, a, e))
            for x, y in zip(a, e):
                if isinstance(y, float):
                    self.assertIsNotNone(x, "%s: got NULL in %r, expected %r" % (what, a, e))
                    self.assertAlmostEqual(x, y, delta=0.011, msg="%s: row %r, expected %r" % (what, a, e))
                else:
                    self.assertEqual(x, y, "%s: row %r, expected %r" % (what, a, e))

    def test_dim_date_has_every_calendar_day(self):
        self.need("dim_date")
        rows = self.q("SELECT date_key, date, year, quarter, month, year_month, weekday_num, weekday "
                      "FROM dim_date ORDER BY date_key")
        expected = []
        for day in calendar(self.raw):
            num = (day.weekday() + 1) % 7
            expected.append((int(day.strftime("%Y%m%d")), day.isoformat(), day.year, (day.month + 2) // 3,
                             day.month, day.strftime("%Y-%m"), num, DAY_NAMES[num]))
        self.assertGreater(len(expected), len({r["order_date"] for r in self.raw}), "data should have days with no sales")
        self.assertEqual(len(rows), len(expected),
                         "dim_date needs every day from %s to %s, not only days with sales" % (expected[0][1], expected[-1][1]))
        self.assertEqual(rows, expected, "check date_key, quarter and the weekday columns (0 = Sunday)")

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

    def test_fact_holds_only_keys_and_numbers(self):
        self.need("fact_sales")
        cols = {r[1] for r in self.q("PRAGMA table_info(fact_sales)")}
        extra = sorted(cols - FACT_COLUMNS)
        self.assertEqual(extra, [], "fact_sales should hold only keys and numbers; move %s to a dimension" % extra)
        self.assertEqual(sorted(FACT_COLUMNS - cols), [], "fact_sales is missing columns")
        for col in sorted(FACT_COLUMNS):
            bad = self.q("SELECT COUNT(*) FROM fact_sales WHERE typeof(%s) NOT IN ('integer', 'real')" % col)[0][0]
            self.assertEqual(bad, 0, "fact_sales.%s has %d values that are not numbers (text or NULL)" % (col, bad))

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
        self.assertEqual(qty, sum(r["quantity"] for r in self.raw), "units in the model must equal units in the export")
        self.assertAlmostEqual(revenue, sum(line_revenue(r) for r in self.raw), delta=0.01,
                               msg="revenue in the model must equal revenue in the export")

    def test_revenue_by_category_month(self):
        self.need(*MODEL)
        totals = {}
        for r in self.raw:
            key = (r["order_date"][:7], r["category"])
            totals[key] = totals.get(key, 0) + line_revenue(r)
        expected = [(k[0], k[1], round(v, 2)) for k, v in sorted(totals.items())]
        self.assertRowsClose(self.run_named("revenue_by_category_month"), expected, "revenue_by_category_month")

    def test_orders_by_region_counts_orders_not_lines(self):
        self.need(*MODEL)
        orders, lines, revenue = {}, {}, {}
        for r in self.raw:
            orders.setdefault(r["region"], set()).add(r["order_id"])
            lines[r["region"]] = lines.get(r["region"], 0) + 1
            revenue[r["region"]] = revenue.get(r["region"], 0) + line_revenue(r)
        expected = [(g, len(orders[g]), lines[g], round(revenue[g], 2)) for g in sorted(orders)]
        actual = self.run_named("orders_by_region")
        if actual and len(actual[0]) == 4 and actual[0][1] == actual[0][2] != expected[0][1]:
            self.fail("orders equals order_lines: count DISTINCT order_id, because one order has several lines")
        self.assertRowsClose(actual, expected, "orders_by_region")

    def test_revenue_by_weekday_keeps_empty_days(self):
        self.need(*MODEL)
        by_date = {}
        for r in self.raw:
            by_date[r["order_date"]] = by_date.get(r["order_date"], 0) + line_revenue(r)
        days, revenue = {}, {}
        for day in calendar(self.raw):
            num = (day.weekday() + 1) % 7
            days[num] = days.get(num, 0) + 1
            revenue[num] = revenue.get(num, 0) + by_date.get(day.isoformat(), 0)
        expected = [(n, DAY_NAMES[n], days[n], round(float(revenue[n]), 2)) for n in sorted(days)]
        actual = self.run_named("revenue_by_weekday")
        self.assertRowsClose(actual, expected, "revenue_by_weekday (start FROM dim_date and LEFT JOIN the facts; "
                                               "count days with COUNT(DISTINCT date_key))")


class TestCommittedData(StarChecks, unittest.TestCase):
    raw = read_csv("transactions")

    def test_sunday_is_in_the_chart_with_zero_revenue(self):
        self.need(*MODEL)
        sql = self.queries.get("revenue_by_weekday", "")
        if not sql:
            self.fail("query 'revenue_by_weekday' is empty: write it first")
        rows = {r[1]: r for r in self.q(sql)}
        self.assertIn("Sun", rows, "Sunday has no sales but must still appear, with revenue 0")
        self.assertEqual(rows["Sun"][3], 0, "Sunday revenue should be 0, not NULL")


class TestSecondDataset(StarChecks, unittest.TestCase):
    """Built in memory with another seed: hard-coded answers fail here."""
    raw = rows_from_build(SECOND_SEED)


TINY = [
    # order_id, line_no, order_date, product, category, unit_price, region, region_manager, quantity
    (1, 1, "2025-03-01", "Desk Lamp", "Lighting", 34.5, "North", "Amara Osei", 2),
    (1, 2, "2025-03-01", "Oak Shelf", "Storage", 64.0, "North", "Amara Osei", 0),
    (2, 1, "2025-03-03", "Desk Lamp", "Lighting", 34.5, "South", "Diego Ramos", 2),
    (3, 1, "2025-04-01", "Oak Shelf", "Storage", 64.0, "South", "Diego Ramos", 1),
]


class TestTinyEdgeCases(StarChecks, unittest.TestCase):
    """A Sunday gap, a line with zero quantity, an order with two lines, and two regions tied on March revenue."""
    raw = [dict(zip(["order_id", "line_no", "order_date", "product", "category", "unit_price",
                     "region", "region_manager", "quantity"], t)) for t in TINY]


if __name__ == "__main__":
    unittest.main()
