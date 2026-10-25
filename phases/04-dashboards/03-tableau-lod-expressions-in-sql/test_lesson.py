"""Tests for lesson 03: Tableau LOD expressions in SQL.

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




class TestLod(SqlTestCase):
    def setUp(self):
        self.orders = read_csv("orders")
        self.first = {}
        self.cust_sales = {}
        self.region_of = {}
        for r in self.orders:
            c, m = r["customer_id"], r["order_date"][:7]
            self.first[c] = min(self.first.get(c, m), m)
            self.cust_sales[c] = self.cust_sales.get(c, 0) + r["amount"]
            self.region_of[c] = r["region"]

    def test_customer_first_month(self):
        expected = sorted(self.first.items())
        self.assertRowsEqual(self.run_query("customer_first_month"), expected)

    def test_new_customers_by_month(self):
        counts = {}
        for m in self.first.values():
            counts[m] = counts.get(m, 0) + 1
        expected = sorted(counts.items())
        active = {}
        for r in self.orders:
            active.setdefault(r["order_date"][:7], set()).add(r["customer_id"])
        self.assertNotEqual([len(active[m]) for m, _ in expected], [n for _, n in expected],
                            "data should have repeat customers")
        self.assertRowsEqual(self.run_query("new_customers_by_month"), expected)

    def test_avg_customer_sales_by_region(self):
        expected = []
        for region in sorted(set(self.region_of.values())):
            vals = [v for c, v in self.cust_sales.items() if self.region_of[c] == region]
            expected.append((region, len(vals), round(sum(vals) / len(vals), 2)))
        self.assertRowsEqual(self.run_query("avg_customer_sales_by_region"), expected)

    def test_region_month_share(self):
        monthly, region_total = {}, {}
        for r in self.orders:
            key = (r["region"], r["order_date"][:7])
            monthly[key] = monthly.get(key, 0) + r["amount"]
            region_total[r["region"]] = region_total.get(r["region"], 0) + r["amount"]
        expected = [(k[0], k[1], round(v, 2), round(region_total[k[0]], 2), round(v / region_total[k[0]], 4))
                    for k, v in sorted(monthly.items())]
        self.assertRowsEqual(self.run_query("region_month_share"), expected, tol=0.0002)

    def test_customer_share_of_region(self):
        region_total = {}
        for c, v in self.cust_sales.items():
            region_total[self.region_of[c]] = region_total.get(self.region_of[c], 0) + v
        rows = sorted(self.cust_sales.items(), key=lambda kv: (self.region_of[kv[0]], -round(kv[1], 2), kv[0]))
        expected = [(c, self.region_of[c], round(v, 2), round(region_total[self.region_of[c]], 2),
                     round(v / region_total[self.region_of[c]], 4)) for c, v in rows]
        self.assertRowsEqual(self.run_query("customer_share_of_region"), expected, tol=0.0002)


if __name__ == "__main__":
    unittest.main()
