"""Tests for lesson 02: joins without losing rows.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

The expected answers are computed with plain Python dictionaries and sets,
never with a join. Your queries run on three kinds of data:
1. the committed data/*.csv,
2. a second dataset built in memory with make_data.build(seed=2026), so a
   query that just types out the answers cannot pass,
3. tiny hand-made tables for the edge cases: empty tables, a guest order with
   no customer (the NOT IN trap), a buyer with no saved address, an order
   with no amount, and a customer with three saved addresses (fan-out).
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

TABLES = {
    "customers": ["customer_id", "signup_date"],
    "orders": ["order_id", "customer_id", "amount"],
    "customer_addresses": ["customer_id", "city", "is_primary"],
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


# The reference answers, written without any join.

def ref_row_counts(d):
    per_key = {}
    for c in d["customers"]:
        per_key[c["customer_id"]] = per_key.get(c["customer_id"], 0) + 1
    inner = sum(per_key.get(o["customer_id"], 0) for o in d["orders"] if o["customer_id"] is not None)
    ordered = {o["customer_id"] for o in d["orders"]}
    unmatched = sum(1 for c in d["customers"] if c["customer_id"] not in ordered)
    return [(len(d["customers"]), len(d["orders"]), inner, inner + unmatched)]


def ref_customer_totals(d):
    spend = {}
    for o in d["orders"]:
        s = spend.setdefault(o["customer_id"], [0, 0.0])
        s[0] += 1
        if o["amount"] is not None:
            s[1] += o["amount"]
    out = []
    for c in sorted(d["customers"], key=lambda r: r["customer_id"]):
        n, total = spend.get(c["customer_id"], [0, 0.0])
        out.append((c["customer_id"], n, round(total, 2)))
    return out


def ref_customers_without_orders(d):
    ordered = {o["customer_id"] for o in d["orders"] if o["customer_id"] is not None}
    return sorted((c["customer_id"],) for c in d["customers"] if c["customer_id"] not in ordered)


def ref_revenue_by_city(d):
    primary = {a["customer_id"]: a["city"] for a in d["customer_addresses"] if a["is_primary"] == 1}
    by_city = {}
    for o in d["orders"]:
        city = primary.get(o["customer_id"])  # None when there is no primary address
        if o["amount"] is not None:
            by_city[city] = by_city.get(city, 0.0) + o["amount"]
    return [(c, round(v, 2)) for c, v in sorted(by_city.items(), key=lambda kv: (kv[0] is not None, kv[0] or ""))]


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

    def assertRowsEqual(self, actual, expected, where, tol=0.011):
        self.assertEqual(
            len(actual), len(expected),
            "%s: got %d rows, expected %d. Expected rows start %r" % (where, len(actual), len(expected), expected[:6]),
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
        self.assertRowsEqual(self.run_query(con, "row_counts"), ref_row_counts(d), where + ", row_counts")
        self.assertRowsEqual(self.run_query(con, "customer_totals"), ref_customer_totals(d), where + ", customer_totals")
        self.assertRowsEqual(self.run_query(con, "customers_without_orders"), ref_customers_without_orders(d),
                             where + ", customers_without_orders")
        self.assertRowsEqual(self.run_query(con, "revenue_by_city"), ref_revenue_by_city(d), where + ", revenue_by_city")


class TestCommittedData(SqlTestCase):
    def setUp(self):
        self.d = {t: read_csv(t) for t in TABLES}
        self.con = make_db(self.d)

    def test_row_counts(self):
        self.assertRowsEqual(self.run_query(self.con, "row_counts"), ref_row_counts(self.d), "row_counts")

    def test_customer_totals_keeps_every_customer(self):
        actual = self.run_query(self.con, "customer_totals")
        self.assertEqual(len(actual), len(self.d["customers"]), "one row per customer: did an inner join drop the non-buyers?")
        self.assertRowsEqual(actual, ref_customer_totals(self.d), "customer_totals")

    def test_customers_without_orders(self):
        self.assertRowsEqual(self.run_query(self.con, "customers_without_orders"), ref_customers_without_orders(self.d),
                             "customers_without_orders")

    def test_revenue_by_city_has_no_fan_out(self):
        actual = self.run_query(self.con, "revenue_by_city")
        total = sum(o["amount"] for o in self.d["orders"])
        got_total = sum(r[1] or 0 for r in actual)
        self.assertAlmostEqual(got_total, total, delta=0.05,
                               msg="city revenue adds to %.2f but orders total %.2f: rows fanned out" % (got_total, total))
        self.assertRowsEqual(actual, ref_revenue_by_city(self.d), "revenue_by_city")


class TestSecondDataset(SqlTestCase):
    def test_same_queries_on_new_data(self):
        d = {t: as_loaded(rows) for t, rows in make_data.build(seed=SECOND_SEED).items()}
        self.check_all(d, "second dataset (seed %d): the same queries on new numbers, so a typed-out answer fails here" % SECOND_SEED)


def customer(cid):
    return {"customer_id": cid, "signup_date": "2026-01-01"}


def order(oid, cid, amount):
    return {"order_id": oid, "customer_id": cid, "amount": amount}


def address(cid, city, primary):
    return {"customer_id": cid, "city": city, "is_primary": primary}


class TestEdgeCases(SqlTestCase):
    def test_empty_tables(self):
        self.check_all({"customers": [], "orders": [], "customer_addresses": []},
                       "empty tables (row_counts is one row of zeros, the rest return no rows)")

    def test_guest_order_with_no_customer(self):
        d = {
            "customers": [customer("C1"), customer("C2")],
            "orders": [order(1, "C1", 20.0), order(2, None, 15.0)],
            "customer_addresses": [address("C1", "Leeds", 1), address("C2", "Pune", 1)],
        }
        self.check_all(d, "order 2 is a guest order with customer_id NULL, and C2 never ordered. "
                          "NOT IN (SELECT customer_id FROM orders) returns nothing when that list holds a NULL: "
                          "use NOT EXISTS or a LEFT JOIN. The guest order's revenue goes in the city NULL row")

    def test_buyer_with_no_address(self):
        d = {
            "customers": [customer("C1"), customer("C2")],
            "orders": [order(1, "C1", 20.0), order(2, "C2", 30.0)],
            "customer_addresses": [address("C1", "Leeds", 1)],
        }
        self.check_all(d, "C2 ordered but saved no address: an inner join to addresses drops their 30.0, "
                          "so revenue_by_city must keep it in a row with city NULL")

    def test_order_with_no_amount(self):
        d = {
            "customers": [customer("C1"), customer("C2")],
            "orders": [order(1, "C1", None), order(2, "C2", 12.5)],
            "customer_addresses": [address("C1", "Leeds", 1), address("C2", "Leeds", 1)],
        }
        self.check_all(d, "C1's only order has no amount: order_count 1, total_spent 0 (COALESCE turns the NULL sum into 0)")

    def test_three_addresses_fan_out(self):
        d = {
            "customers": [customer("C1")],
            "orders": [order(1, "C1", 10.0), order(2, "C1", 5.0)],
            "customer_addresses": [address("C1", "Leeds", 0), address("C1", "Perth", 1), address("C1", "Pune", 0)],
        }
        self.check_all(d, "C1 has three saved addresses, one primary: revenue_by_city is Perth 15.0, not 45.0")


if __name__ == "__main__":
    unittest.main()
