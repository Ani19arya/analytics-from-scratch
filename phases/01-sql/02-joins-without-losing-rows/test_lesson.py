"""Tests for lesson 02: joins without losing rows.

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




class TestJoins(SqlTestCase):
    def setUp(self):
        self.customers = read_csv("customers")
        self.orders = read_csv("orders")
        self.addresses = read_csv("customer_addresses")
        self.spend = {}
        for o in self.orders:
            s = self.spend.setdefault(o["customer_id"], [0, 0.0])
            s[0] += 1
            s[1] += o["amount"]

    def test_row_counts(self):
        never = sum(1 for c in self.customers if c["customer_id"] not in self.spend)
        expected = [(len(self.customers), len(self.orders), len(self.orders), len(self.orders) + never)]
        self.assertRowsEqual(self.run_query("row_counts"), expected)

    def test_customer_totals_keeps_every_customer(self):
        expected = []
        for c in sorted(self.customers, key=lambda r: r["customer_id"]):
            n, total = self.spend.get(c["customer_id"], [0, 0.0])
            expected.append((c["customer_id"], n, round(total, 2)))
        actual = self.run_query("customer_totals")
        self.assertEqual(len(actual), len(self.customers), "one row per customer: did an inner join drop the non-buyers?")
        self.assertRowsEqual(actual, expected)

    def test_customers_without_orders(self):
        expected = sorted((c["customer_id"],) for c in self.customers if c["customer_id"] not in self.spend)
        self.assertRowsEqual(self.run_query("customers_without_orders"), expected)

    def test_revenue_by_city_has_no_fan_out(self):
        primary = {a["customer_id"]: a["city"] for a in self.addresses if a["is_primary"] == 1}
        by_city = {}
        for o in self.orders:
            city = primary[o["customer_id"]]
            by_city[city] = by_city.get(city, 0.0) + o["amount"]
        actual = self.run_query("revenue_by_city")
        total = sum(o["amount"] for o in self.orders)
        got_total = sum(r[1] or 0 for r in actual)
        self.assertAlmostEqual(got_total, total, delta=0.05, msg="city revenue adds to %.2f but orders total %.2f: rows fanned out" % (got_total, total))
        self.assertRowsEqual(actual, [(c, round(v, 2)) for c, v in sorted(by_city.items())])


if __name__ == "__main__":
    unittest.main()
