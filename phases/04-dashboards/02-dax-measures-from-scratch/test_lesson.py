"""Tests for lesson 02: DAX measures from scratch.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

"""
import csv
import os
import re
import sqlite3
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if os.environ.get("CHECK_SOLUTION") == "1":
    SQL_FILE = os.path.join(HERE, "solution", "solution.sql")
else:
    SQL_FILE = os.path.join(HERE, "exercise.sql")


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
    for name in sorted(os.listdir(os.path.join(HERE, "data"))):
        if not name.endswith(".csv"):
            continue
        table = name[:-4]
        rows = read_csv(table)
        cols = list(rows[0].keys())
        con.execute("CREATE TABLE %s (%s)" % (table, ", ".join(cols)))
        con.executemany(
            "INSERT INTO %s VALUES (%s)" % (table, ", ".join("?" * len(cols))),
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
    return {k: v.strip() for k, v in queries.items()}


class SqlTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.con = load_db()
        cls.queries = load_queries(SQL_FILE)

    def run_query(self, name):
        sql = self.queries.get(name, "")
        if not sql:
            self.fail("query '%s' is empty in %s: write it first" % (name, os.path.basename(SQL_FILE)))
        return [tuple(r) for r in self.con.execute(sql).fetchall()]

    def assertRowsEqual(self, actual, expected, tol=0.011):
        self.assertEqual(len(actual), len(expected), "wrong number of rows: got %d, expected %d" % (len(actual), len(expected)))
        for a, e in zip(actual, expected):
            self.assertEqual(len(a), len(e), "wrong number of columns in row %r, expected %r" % (a, e))
            for x, y in zip(a, e):
                if isinstance(y, float):
                    self.assertIsNotNone(x, "got NULL where %r was expected" % (e,))
                    self.assertAlmostEqual(x, y, delta=tol, msg="row %r, expected %r" % (a, e))
                else:
                    self.assertEqual(x, y, "row %r, expected %r" % (a, e))




class TestMeasures(SqlTestCase):
    def setUp(self):
        self.sales = read_csv("sales")

    def monthly(self):
        out = {}
        for r in self.sales:
            out[r["order_date"][:7]] = out.get(r["order_date"][:7], 0) + r["amount"]
        return out

    def test_sales_by_category(self):
        grand = sum(r["amount"] for r in self.sales)
        expected = []
        for cat in sorted({r["category"] for r in self.sales}):
            rows = [r for r in self.sales if r["category"] == cat]
            total = sum(r["amount"] for r in rows)
            online = sum(r["amount"] for r in rows if r["channel"] == "Online")
            expected.append((cat, round(total, 2), round(online, 2), round(total / grand, 4)))
        self.assertRowsEqual(self.run_query("sales_by_category"), expected, tol=0.0002)

    def test_sales_ytd_has_every_month_and_restarts_in_january(self):
        monthly = self.monthly()
        first, last = min(monthly), max(monthly)
        y, m = int(first[:4]), int(first[5:])
        expected, running, year = [], 0, None
        while "%04d-%02d" % (y, m) <= last:
            ym = "%04d-%02d" % (y, m)
            if y != year:
                running, year = 0, y
            sales = monthly.get(ym, 0)
            running += sales
            expected.append((ym, round(float(sales), 2), round(float(running), 2)))
            m += 1
            if m == 13:
                y, m = y + 1, 1
        self.assertIn(0.0, [e[1] for e in expected], "data should contain a month with no sales")
        self.assertRowsEqual(self.run_query("sales_ytd"), expected)

    def test_sales_vs_last_year_matches_calendar_month(self):
        monthly = self.monthly()
        expected = []
        for ym in sorted(k for k in monthly if k >= "2026-01"):
            ly = monthly.get("%04d%s" % (int(ym[:4]) - 1, ym[4:]), 0)
            growth = None if ly == 0 else round((monthly[ym] - ly) * 100.0 / ly, 1)
            expected.append((ym, round(monthly[ym], 2), round(float(ly), 2), growth))
        self.assertIn(None, [e[3] for e in expected], "data should contain a month with no sales last year")
        actual = self.run_query("sales_vs_last_year")
        self.assertRowsEqual(actual, expected, tol=0.051)
        for a, e in zip(actual, expected):
            if e[3] is None:
                self.assertIsNone(a[3], "growth must be NULL when last year had no sales: row %r" % (a,))


if __name__ == "__main__":
    unittest.main()
