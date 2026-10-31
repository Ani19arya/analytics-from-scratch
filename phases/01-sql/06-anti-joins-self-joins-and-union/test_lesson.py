"""Tests for lesson 06: anti-joins, self-joins and UNION.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

The expected answers are computed with plain Python lists, sets and
dictionaries, never with SQL. Your queries run on three kinds of data:
1. the committed data/*.csv,
2. a second dataset built in memory with make_data.build(seed=2026), so a
   query that just types out the answers cannot pass,
3. tiny hand-made tables for the edge cases: empty tables, a guest order
   with no customer in April (the NOT IN trap), a customer who ordered on
   the web in March and in the app in April, two identical rows in the two
   order tables (the UNION trap), a referrer who is not in the customers
   table, and orders on 31 March and 1 April.
"""
import csv
import os
import re
import sqlite3
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_data  # noqa: E402

if os.environ.get("CHECK_SOLUTION") == "1":
    SQL_FILE = os.path.join(HERE, "solution", "solution.sql")
else:
    SQL_FILE = os.path.join(HERE, "exercise.sql")

ORDER_COLS = ["order_id", "customer_id", "order_date", "amount"]
TABLES = {
    "customers": ["customer_id", "name", "city", "referred_by"],
    "web_orders": ORDER_COLS,
    "app_orders": ORDER_COLS,
}
SECOND_SEED = 2026


def cast(value):
    if value is None or value == "":
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


def as_loaded(rows):
    """Values exactly as they would come back from the CSV file."""
    return [{k: cast(None if v is None else str(v)) for k, v in r.items()} for r in rows]


def make_db(data):
    con = sqlite3.connect(":memory:")
    for table, cols in TABLES.items():
        con.execute("CREATE TABLE %s (%s)" % (table, ", ".join(cols)))
        con.executemany(
            "INSERT INTO %s VALUES (%s)" % (table, ", ".join("?" * len(cols))),
            [[r.get(c) for c in cols] for r in data.get(table, [])],
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


# The reference answers, written with Python lists and sets.

def all_orders(d):
    """Every order from both systems. A list, so two identical rows stay two orders."""
    return list(d["web_orders"]) + list(d["app_orders"])


def buyers(d, month):
    """Customers (not guests) with at least one order in month 'YYYY-MM', from either system."""
    return {o["customer_id"] for o in all_orders(d) if o["customer_id"] is not None and o["order_date"][:7] == month}


def ref_monthly_orders(d):
    out = {}
    for o in all_orders(d):
        m = out.setdefault(o["order_date"][:7], [0, 0.0])
        m[0] += 1
        m[1] += o["amount"]
    return [(month, n, round(total, 2)) for month, (n, total) in sorted(out.items())]


def ref_lapsed_customers(d):
    names = {c["customer_id"]: c["name"] for c in d["customers"]}
    lapsed = buyers(d, "2026-03") - buyers(d, "2026-04")
    out = []
    for c in sorted(d["customers"], key=lambda r: r["customer_id"]):
        if c["customer_id"] in lapsed:
            out.append((c["customer_id"], c["name"], names.get(c["referred_by"])))
    return out


def ref_summary(d):
    march, april = buyers(d, "2026-03"), buyers(d, "2026-04")
    return [(len(march), len(april), len(march & april), len(march - april), len(march | april))]


class SqlTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.queries = load_queries(SQL_FILE)

    def run_query(self, con, name):
        sql = self.queries.get(name, "")
        if not sql:
            self.fail("query '%s' is empty in %s: write it first" % (name, os.path.basename(SQL_FILE)))
        try:
            return [tuple(r) for r in con.execute(sql).fetchall()]
        except sqlite3.Error as e:
            self.fail("query '%s' did not run: %s" % (name, e))

    def assertRowsEqual(self, actual, expected, where, tol=0.0051):
        self.assertEqual(
            len(actual), len(expected),
            "%s: got %d rows, expected %d. Expected rows start %r" % (where, len(actual), len(expected), expected[:4]),
        )
        for a, e in zip(actual, expected):
            self.assertEqual(len(a), len(e), "%s: row %r has the wrong number of columns, expected %r" % (where, a, e))
            for x, y in zip(a, e):
                if isinstance(y, float):
                    self.assertIsNotNone(x, "%s: got NULL in row %r, expected %r" % (where, a, e))
                    self.assertAlmostEqual(x, y, delta=tol, msg="%s: row %r, expected %r" % (where, a, e))
                else:
                    self.assertEqual(x, y, "%s: row %r, expected %r" % (where, a, e))

    def check_all(self, d, where):
        con = make_db(d)
        self.assertRowsEqual(self.run_query(con, "monthly_orders"), ref_monthly_orders(d), where + ", monthly_orders")
        self.assertRowsEqual(self.run_query(con, "lapsed_customers"), ref_lapsed_customers(d), where + ", lapsed_customers")
        self.assertRowsEqual(self.run_query(con, "march_april_summary"), ref_summary(d), where + ", march_april_summary")


class TestCommittedData(SqlTestCase):
    def setUp(self):
        self.d = {t: read_csv(t) for t in TABLES}
        self.con = make_db(self.d)

    def test_monthly_orders(self):
        got = self.run_query(self.con, "monthly_orders")
        self.assertEqual(sum(r[1] for r in got), len(all_orders(self.d)),
                         "monthly_orders should count every row of web_orders and app_orders: stack them with "
                         "UNION ALL, because UNION merges rows that look the same")
        self.assertRowsEqual(got, ref_monthly_orders(self.d), "monthly_orders")

    def test_lapsed_customers(self):
        got = self.run_query(self.con, "lapsed_customers")
        self.assertTrue(got, "lapsed_customers returned no rows: NOT IN against a list that holds a NULL (the "
                             "guest orders) is never true, so use NOT EXISTS or a LEFT JOIN ... IS NULL")
        self.assertRowsEqual(got, ref_lapsed_customers(self.d),
                             "lapsed_customers (check both order tables, and keep customers nobody referred)")

    def test_summary(self):
        self.assertRowsEqual(self.run_query(self.con, "march_april_summary"), ref_summary(self.d),
                             "march_april_summary (either_month counts each customer once)")


class TestSecondDataset(SqlTestCase):
    def test_same_queries_on_new_data(self):
        d = {t: as_loaded(rows) for t, rows in make_data.build(seed=SECOND_SEED).items()}
        self.check_all(d, "second dataset (seed %d)" % SECOND_SEED)


def customer(cid, name, referred_by=None):
    return {"customer_id": cid, "name": name, "city": "Pune", "referred_by": referred_by}


def order(oid, cid, day, amount=24.0):
    return {"order_id": oid, "customer_id": cid, "order_date": day, "amount": amount}


class TestEdgeCases(SqlTestCase):
    def test_empty_tables(self):
        self.check_all({"customers": [], "web_orders": [], "app_orders": []},
                       "empty tables (no months, no lapsed customers, a summary of zeros)")

    def test_guest_order_in_april(self):
        d = {
            "customers": [customer("C1", "Ana"), customer("C2", "Ben")],
            "web_orders": [order(1, "C1", "2026-03-04"), order(2, "C2", "2026-03-09"),
                           order(3, "C2", "2026-04-02"), order(4, None, "2026-04-05")],
            "app_orders": [],
        }
        self.check_all(d, "a guest order (customer_id NULL) in April: Ana must still be listed as lapsed. "
                          "NOT IN with a NULL in the list returns no rows")

    def test_switched_channel(self):
        d = {
            "customers": [customer("C1", "Ana"), customer("C2", "Ben")],
            "web_orders": [order(1, "C1", "2026-03-10"), order(2, "C2", "2026-03-12")],
            "app_orders": [order(1, "C1", "2026-04-20")],
        }
        self.check_all(d, "Ana ordered on the web in March and in the app in April, so she is not lapsed: "
                          "check both order tables")

    def test_identical_rows_in_both_systems(self):
        d = {
            "customers": [customer("C1", "Ana")],
            "web_orders": [order(7, "C1", "2026-03-15", 48.0)],
            "app_orders": [order(7, "C1", "2026-03-15", 48.0)],
        }
        self.check_all(d, "web order 7 and app order 7 are two real orders that happen to look the same: March "
                          "has 2 orders and 96.0 revenue, so stack with UNION ALL, not UNION")

    def test_referrers(self):
        d = {
            "customers": [customer("C1", "Ana"), customer("C2", "Ben", "C1"), customer("C3", "Cy", "C9"),
                          customer("C4", "Dee", "C2")],
            "web_orders": [order(1, "C1", "2026-03-01"), order(2, "C2", "2026-03-02"), order(3, "C3", "2026-03-03"),
                           order(4, "C4", "2026-03-04"), order(5, "C1", "2026-04-01")],
            "app_orders": [],
        }
        self.check_all(d, "Ben was referred by Ana, Dee by Ben, Cy by C9 who is not in customers (referrer_name "
                          "NULL): use a LEFT self-join so nobody drops out")

    def test_month_edges(self):
        d = {
            "customers": [customer("C1", "Ana"), customer("C2", "Ben"), customer("C3", "Cy")],
            "web_orders": [order(1, "C1", "2026-03-31"), order(2, "C2", "2026-02-28"), order(3, "C2", "2026-04-30"),
                           order(4, "C3", "2026-03-01"), order(5, "C3", "2026-05-01")],
            "app_orders": [],
        }
        self.check_all(d, "orders on 31 March and 1 March count as March; 30 April counts as April and "
                          "1 May does not")


if __name__ == "__main__":
    unittest.main()
