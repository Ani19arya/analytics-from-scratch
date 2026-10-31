"""Tests for lesson 01: GROUP BY from raw rows.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

The expected answers are computed with a plain Python loop, so the test is
also a second, independent way of doing GROUP BY. Your queries run on three
kinds of data:
1. the committed data/orders.csv,
2. a second dataset built in memory with make_data.build(seed=2026), so a
   query that just types out the answers cannot pass,
3. tiny hand-made tables for the edge cases: no rows, a city on exactly 70
   orders, a city with no completed orders, a missing amount, a tie.
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

COLUMNS = ["order_id", "customer_id", "city", "order_date", "amount", "status"]
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


def make_db(rows):
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE orders (%s)" % ", ".join(COLUMNS))
    con.executemany(
        "INSERT INTO orders VALUES (%s)" % ", ".join("?" * len(COLUMNS)),
        [[r.get(c) for c in COLUMNS] for r in rows],
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


# The reference answers: GROUP BY written as a loop with a dictionary.

def ref_status_counts(rows):
    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return sorted(counts.items())


def city_buckets(rows):
    buckets = {}
    for row in rows:
        if row["status"] != "completed":  # WHERE
            continue
        b = buckets.setdefault(row["city"], {"orders": 0, "revenue": 0.0, "priced": 0})  # GROUP BY
        b["orders"] += 1  # COUNT(*)
        if row["amount"] is not None:  # SUM and AVG skip NULLs
            b["revenue"] += row["amount"]
            b["priced"] += 1
    return buckets


def ref_city_totals(rows):
    return [
        (city, b["orders"], round(b["revenue"], 2), round(b["revenue"] / b["priced"], 2))
        for city, b in sorted(city_buckets(rows).items())
    ]


def ref_busy_cities(rows, threshold=70):
    kept = [(c, b["orders"], round(b["revenue"], 2)) for c, b in city_buckets(rows).items() if b["orders"] >= threshold]
    return sorted(kept, key=lambda r: (-r[2], r[0]))


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
            "%s: got %d rows, expected %d. Expected rows: %r" % (where, len(actual), len(expected), expected[:6]),
        )
        for a, e in zip(actual, expected):
            self.assertEqual(len(a), len(e), "%s: row %r has the wrong number of columns, expected %r" % (where, a, e))
            for x, y in zip(a, e):
                if isinstance(y, float):
                    self.assertIsNotNone(x, "%s: got NULL in row %r, expected %r" % (where, a, e))
                    self.assertAlmostEqual(x, y, delta=tol, msg="%s: row %r, expected %r" % (where, a, e))
                else:
                    self.assertEqual(x, y, "%s: row %r, expected %r" % (where, a, e))

    def check_all(self, rows, where):
        con = make_db(rows)
        self.assertRowsEqual(self.run_query(con, "status_counts"), ref_status_counts(rows), where + ", status_counts")
        self.assertRowsEqual(self.run_query(con, "city_totals"), ref_city_totals(rows), where + ", city_totals")
        self.assertRowsEqual(self.run_query(con, "busy_cities"), ref_busy_cities(rows), where + ", busy_cities")


class TestCommittedData(SqlTestCase):
    def setUp(self):
        self.rows = read_csv("orders")
        self.con = make_db(self.rows)

    def test_status_counts(self):
        self.assertRowsEqual(self.run_query(self.con, "status_counts"), ref_status_counts(self.rows), "status_counts")

    def test_city_totals(self):
        self.assertRowsEqual(self.run_query(self.con, "city_totals"), ref_city_totals(self.rows), "city_totals")

    def test_busy_cities(self):
        # Any correct form passes: HAVING, or WHERE on a grouped subquery.
        self.assertRowsEqual(self.run_query(self.con, "busy_cities"), ref_busy_cities(self.rows), "busy_cities")


class TestSecondDataset(SqlTestCase):
    def test_same_queries_on_new_data(self):
        rows = as_loaded(make_data.build(seed=SECOND_SEED)["orders"])
        self.check_all(rows, "second dataset (seed %d): the same queries on new numbers, so a typed-out answer fails here" % SECOND_SEED)


def order(i, city, amount, status="completed"):
    return {"order_id": i, "customer_id": "C001", "city": city, "order_date": "2026-07-01", "amount": amount, "status": status}


class TestEdgeCases(SqlTestCase):
    def test_empty_table(self):
        self.check_all([], "empty orders table (every query should return no rows)")

    def test_threshold_is_at_least_70(self):
        rows = [order(i, "Oslo", 10.0) for i in range(70)] + [order(100 + i, "Rome", 10.0) for i in range(69)]
        self.check_all(rows, "Oslo has exactly 70 completed orders and must be kept (>= 70), Rome has 69")

    def test_city_with_no_completed_orders(self):
        rows = [order(1, "Lima", 50.0), order(2, "Kobe", 30.0, "refunded"), order(3, "Kobe", 20.0, "cancelled")]
        self.check_all(rows, "Kobe has only refunded and cancelled orders, so it has no completed revenue row")

    def test_missing_amount(self):
        rows = [order(1, "Lima", 10.0), order(2, "Lima", 20.0), order(3, "Lima", None)]
        self.check_all(rows, "Lima has 3 completed orders but one has no amount: orders 3, revenue 30.0, avg_order 15.0 (AVG skips NULL)")

    def test_tie_on_revenue(self):
        rows = [order(i, "Zug", 10.0) for i in range(70)] + [order(100 + i, "Bern", 10.0) for i in range(70)]
        self.check_all(rows, "Bern and Zug tie on revenue 700.0: break the tie by city name")


if __name__ == "__main__":
    unittest.main()
