"""Tests for lesson 07: subqueries and CTEs.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

The expected answers are computed with plain Python dictionaries, never with
SQL. Your queries run on three kinds of data:
1. the committed data/*.csv,
2. a second dataset built in memory with make_data.build(seed=2026), so a
   query that just types out the answers cannot pass,
3. tiny hand-made tables for the edge cases: empty tables, a customer exactly
   at the city average (a tie, not above), a city with one customer, a
   customer with no orders (not part of the average), and a city where the
   average order is small but the average customer spends a lot (the grain
   trap).
"""
import csv
import math
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

TABLES = {"customers": ["customer_id", "name", "city"], "orders": ["order_id", "customer_id", "order_date", "amount"]}
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


def round2(x):
    """Round to 2 decimals, halves away from zero, the way SQLite's ROUND does."""
    return math.floor(x * 100 + 0.5) / 100


# The reference answers: totals per customer first, then averages of those totals.

def totals(d):
    """{customer_id: [orders, total]} for customers who are in customers and placed an order."""
    known = {c["customer_id"] for c in d["customers"]}
    out = {}
    for o in d["orders"]:
        if o["customer_id"] in known:
            t = out.setdefault(o["customer_id"], [0, 0])
            t[0] += 1
            t[1] += o["amount"]
    return out


def averages(d):
    """{city: (customers, exact average of their totals)}"""
    city = {c["customer_id"]: c["city"] for c in d["customers"]}
    sums = {}
    for cid, (_, total) in totals(d).items():
        s = sums.setdefault(city[cid], [0, 0])
        s[0] += 1
        s[1] += total
    return {k: (n, total / n) for k, (n, total) in sums.items()}


def ref_customer_totals(d):
    city = {c["customer_id"]: c["city"] for c in d["customers"]}
    return [(cid, city[cid], n, total) for cid, (n, total) in sorted(totals(d).items())]


def ref_city_averages(d):
    return [(city, n, round2(avg)) for city, (n, avg) in sorted(averages(d).items())]


def ref_above_average(d):
    info = {c["customer_id"]: c for c in d["customers"]}
    avg = averages(d)
    rows = []
    for cid, (_, total) in totals(d).items():
        c = info[cid]
        if total > avg[c["city"]][1]:  # strictly more than the exact average: a tie is not above
            rows.append((cid, c["name"], c["city"], total, round2(avg[c["city"]][1])))
    return sorted(rows, key=lambda r: (r[2], -r[3], r[0]))


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
        self.assertRowsEqual(self.run_query(con, "customer_totals"), ref_customer_totals(d), where + ", customer_totals")
        self.assertRowsEqual(self.run_query(con, "city_averages"), ref_city_averages(d), where + ", city_averages")
        self.assertRowsEqual(self.run_query(con, "above_average"), ref_above_average(d), where + ", above_average")


class TestCommittedData(SqlTestCase):
    def setUp(self):
        self.d = {t: read_csv(t) for t in TABLES}
        self.con = make_db(self.d)

    def test_customer_totals(self):
        got = self.run_query(self.con, "customer_totals")
        self.assertEqual(sum(r[3] for r in got), sum(o["amount"] for o in self.d["orders"]),
                         "customer_totals should add up to the total of the orders table: one row per customer, "
                         "every order counted once")
        self.assertRowsEqual(got, ref_customer_totals(self.d), "customer_totals")

    def test_city_averages(self):
        self.assertRowsEqual(self.run_query(self.con, "city_averages"), ref_city_averages(self.d),
                             "city_averages (average the customer totals, not the order amounts)")

    def test_above_average(self):
        self.assertRowsEqual(self.run_query(self.con, "above_average"), ref_above_average(self.d),
                             "above_average (compare each customer with the average of their own city)")


class TestSecondDataset(SqlTestCase):
    def test_same_queries_on_new_data(self):
        d = {t: as_loaded(rows) for t, rows in make_data.build(seed=SECOND_SEED).items()}
        self.check_all(d, "second dataset (seed %d)" % SECOND_SEED)


def customer(cid, city):
    return {"customer_id": cid, "name": "Name " + cid, "city": city}


def orders_for(spec):
    """spec: list of (customer_id, amount) -> order rows."""
    return [{"order_id": n, "customer_id": cid, "order_date": "2026-10-%02d" % (n % 28 + 1), "amount": amt}
            for n, (cid, amt) in enumerate(spec, 1)]


class TestEdgeCases(SqlTestCase):
    def test_empty_tables(self):
        self.check_all({"customers": [], "orders": []}, "empty tables (every query returns no rows)")

    def test_tie_at_the_average(self):
        d = {"customers": [customer("A", "Pune"), customer("B", "Pune"), customer("C", "Pune")],
             "orders": orders_for([("A", 200), ("B", 300), ("C", 400)])}
        self.check_all(d, "totals 200, 300 and 400 average 300: B spent exactly the average, which is not MORE "
                          "than it, so only C is above")

    def test_one_customer_city(self):
        d = {"customers": [customer("A", "Nagpur"), customer("B", "Pune"), customer("C", "Pune")],
             "orders": orders_for([("A", 900), ("B", 100), ("C", 500)])}
        self.check_all(d, "A is the only Nagpur customer, so A is the Nagpur average and is not above it; compare "
                          "with your own city, not with everyone")

    def test_customer_without_orders(self):
        d = {"customers": [customer("A", "Pune"), customer("B", "Pune"), customer("Z", "Pune")],
             "orders": orders_for([("A", 300), ("B", 500)])}
        self.check_all(d, "Z placed no order: Z is not in customer_totals and does not pull the Pune average down "
                          "to 266.67 (it is 400.0)")

    def test_grain(self):
        d = {"customers": [customer("A", "Mumbai"), customer("B", "Mumbai")],
             "orders": orders_for([("A", 100)] * 10 + [("B", 600)])}
        self.check_all(d, "A has ten orders of 100 and B one of 600: the average customer spends 800.0, so A (1000) "
                          "is above and B is not. The average order (145.45) is the wrong yardstick")


if __name__ == "__main__":
    unittest.main()
