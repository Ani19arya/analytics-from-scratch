"""Tests for lesson 00-05: NULLs, CASE and COALESCE.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

An empty CSV cell is loaded as NULL (None in Python). The expected answers are
worked out here in plain Python, never copied from the solution. Every query
also runs on a second dataset and on small hand-made tables.
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

SECOND_SEED = 6
COLUMNS = ["order_id", "order_date", "city", "status", "amount", "delivered_date", "tip"]


def cast(value):
    if value == "":
        return None
    for kind in (int, float):
        try:
            return kind(value)
        except ValueError:
            pass
    return value


def typed(rows):
    return [{k: cast(v) for k, v in r.items()} for r in rows]


def committed():
    with open(os.path.join(HERE, "data", "orders.csv"), newline="") as f:
        return typed(csv.DictReader(f))


def make_db(rows):
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE orders (%s)" % ", ".join(COLUMNS))
    con.executemany("INSERT INTO orders VALUES (%s)" % ", ".join("?" * len(COLUMNS)), [[r.get(c) for c in COLUMNS] for r in rows])
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


QUERIES = load_queries(SQL_FILE)
NAMES = ["delivery_date_counts", "orders_without_delivery_date", "order_sizes", "size_counts", "tip_summary"]


def run(con, name):
    sql = QUERIES.get(name, "")
    if not sql:
        raise AssertionError("query '%s' is empty in %s: write it first" % (name, os.path.basename(SQL_FILE)))
    return [tuple(r) for r in con.execute(sql).fetchall()]


# Plain Python references.
def size_of(amount):
    if amount is None:
        return "unknown"
    if amount < 300:
        return "small"
    if amount < 800:
        return "medium"
    return "large"


def ref_counts(rows):
    without = sum(1 for r in rows if r["delivered_date"] is None)
    return [(len(rows), len(rows) - without, without)]


def ref_without(rows):
    return [(r["order_id"], r["status"]) for r in sorted(rows, key=lambda r: r["order_id"]) if r["delivered_date"] is None]


def ref_sizes(rows):
    return [(r["order_id"], r["amount"], size_of(r["amount"])) for r in sorted(rows, key=lambda r: r["order_id"])]


def ref_size_counts(rows):
    sizes = [size_of(r["amount"]) for r in rows]
    return [tuple(sizes.count(s) for s in ("small", "medium", "large", "unknown"))]


def ref_tips(rows):
    tips = [r["tip"] for r in rows if r["tip"] is not None]
    if not tips:
        return [(0, None, round(0, 2) if rows else None)]
    return [(len(tips), round(sum(tips) / len(tips), 2), round(sum(tips) / len(rows), 2))]


def row(order_id, status="delivered", amount=100.0, delivered_date="2026-10-20", tip=None):
    return {"order_id": order_id, "order_date": "2026-10-20", "city": "Pune", "status": status,
            "amount": amount, "delivered_date": delivered_date, "tip": tip}


class Checks:
    def compare(self, got, exp, what):
        self.assertEqual(len(got), len(exp), "%s: got %d rows, expected %d" % (what, len(got), len(exp)))
        for g, e in zip(got, exp):
            self.assertEqual(len(g), len(e), "%s: row %r should have the columns of %r" % (what, g, e))
            for a, b in zip(g, e):
                if isinstance(b, float):
                    self.assertIsNotNone(a, "%s: got NULL in %r where %r was expected" % (what, g, e))
                    self.assertAlmostEqual(a, b, delta=0.011, msg="%s: row %r, expected %r" % (what, g, e))
                else:
                    self.assertEqual(a, b, "%s: row %r, expected %r" % (what, g, e))

    def check_all(self, rows, label):
        con = make_db(rows)
        self.compare(run(con, "delivery_date_counts"), ref_counts(rows), label + ", delivery_date_counts (COUNT(*) vs COUNT(column))")
        self.compare(run(con, "orders_without_delivery_date"), ref_without(rows), label + ", orders_without_delivery_date (use IS NULL)")
        self.compare(run(con, "order_sizes"), ref_sizes(rows), label + ", order_sizes (check the order of the WHEN lines and the NULL case)")
        self.compare(run(con, "size_counts"), ref_size_counts(rows), label + ", size_counts")
        self.compare(run(con, "tip_summary"), ref_tips(rows), label + ", tip_summary")


class TestOnData(unittest.TestCase, Checks):
    def test_lesson_data(self):
        self.check_all(committed(), "lesson data")

    def test_second_dataset(self):
        self.check_all(typed(make_data.build(SECOND_SEED)["orders"]), "second dataset")


class TestSmallCases(unittest.TestCase, Checks):
    def test_bucket_edges(self):
        rows = [row(1, amount=299.99), row(2, amount=300.0), row(3, amount=799.99), row(4, amount=800.0),
                row(5, amount=0.0), row(6, amount=None)]
        self.compare(run(make_db(rows), "order_sizes"),
                     [(1, 299.99, "small"), (2, 300.0, "medium"), (3, 799.99, "medium"), (4, 800.0, "large"),
                      (5, 0.0, "small"), (6, None, "unknown")],
                     "300 is medium, 800 is large, 0 is small and a NULL amount is unknown")
        self.compare(run(make_db(rows), "size_counts"), [(2, 2, 1, 1)], "size_counts on the edge cases")

    def test_all_null_dates(self):
        rows = [row(1, status="cancelled", delivered_date=None), row(2, status="in_transit", delivered_date=None)]
        con = make_db(rows)
        self.compare(run(con, "delivery_date_counts"), [(2, 0, 2)], "two orders, neither has a date")
        self.compare(run(con, "orders_without_delivery_date"), [(1, "cancelled"), (2, "in_transit")], "both orders have no date")

    def test_zero_tip_is_not_a_missing_tip(self):
        rows = [row(1, tip=0), row(2, tip=30), row(3, tip=None), row(4, tip=None)]
        self.compare(run(make_db(rows), "tip_summary"), [(2, 15.0, 7.5)],
                     "a tip of 0 is recorded (count it), a NULL tip is not: AVG(tip) = 30/2, AVG(COALESCE(tip, 0)) = 30/4")

    def test_empty_table(self):
        con = make_db([])
        self.compare(run(con, "delivery_date_counts"), [(0, 0, 0)], "an empty table has 0 orders")
        self.assertEqual(run(con, "orders_without_delivery_date"), [], "an empty table has no orders to list")
        self.assertEqual(run(con, "order_sizes"), [], "an empty table has no orders to size")


if __name__ == "__main__":
    unittest.main()
