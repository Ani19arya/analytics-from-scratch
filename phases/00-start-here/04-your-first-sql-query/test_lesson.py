"""Tests for lesson 00-04: your first SQL query.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

The expected rows are worked out here in plain Python (a filter, a sort and a
slice), never copied from the solution. Every query also runs on a second
dataset built by make_data.build(seed) and on small hand-made tables.
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

SECOND_SEED = 29
START, END = "2026-10-19", "2026-10-25"
COLUMNS = ["order_id", "order_date", "city", "status", "amount"]


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
    con.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", [[r[c] for c in COLUMNS] for r in rows])
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


def run(con, name):
    sql = QUERIES.get(name, "")
    if not sql:
        raise AssertionError("query '%s' is empty in %s: write it first" % (name, os.path.basename(SQL_FILE)))
    return [tuple(r) for r in con.execute(sql).fetchall()]


def last_week_delivered(rows):
    return [r for r in rows if r["status"] == "delivered" and START <= r["order_date"] <= END]


def ref_first_look(rows):
    return [tuple(r[c] for c in COLUMNS) for r in sorted(rows, key=lambda r: r["order_id"])[:5]]


def ref_top_ten(rows):
    keep = sorted(last_week_delivered(rows), key=lambda r: (-r["amount"], r["order_id"]))[:10]
    return [(r["order_id"], r["order_date"], r["city"], r["amount"]) for r in keep]


def ref_big(rows):
    keep = [r for r in last_week_delivered(rows) if r["amount"] >= 1000 and r["city"] in ("Pune", "Nagpur")]
    return [(r["order_id"], r["city"], r["amount"]) for r in sorted(keep, key=lambda r: r["order_id"])]


def row(order_id, date, city, status, amount):
    return {"order_id": order_id, "order_date": date, "city": city, "status": status, "amount": amount}


class Checks:
    def compare(self, got, exp, what):
        self.assertEqual(len(got), len(exp), "%s: got %d rows, expected %d" % (what, len(got), len(exp)))
        for g, e in zip(got, exp):
            self.assertEqual(len(g), len(e), "%s: row %r should have the columns of %r" % (what, g, e))
            for a, b in zip(g, e):
                if isinstance(b, float):
                    self.assertAlmostEqual(a, b, delta=0.001, msg="%s: row %r, expected %r" % (what, g, e))
                else:
                    self.assertEqual(a, b, "%s: row %r, expected %r (check the columns, the filter and the sort)" % (what, g, e))

    def check_all(self, rows, label):
        con = make_db(rows)
        self.compare(run(con, "first_look"), ref_first_look(rows), label + ", first_look")
        self.compare(run(con, "top_ten_last_week"), ref_top_ten(rows), label + ", top_ten_last_week")
        self.compare(run(con, "big_orders_pune_nagpur"), ref_big(rows), label + ", big_orders_pune_nagpur")


class TestOnData(unittest.TestCase, Checks):
    def test_lesson_data(self):
        self.check_all(committed(), "lesson data")

    def test_second_dataset(self):
        self.check_all(typed(make_data.build(SECOND_SEED)["orders"]), "second dataset")


class TestSmallCases(unittest.TestCase, Checks):
    def test_empty_table(self):
        con = make_db([])
        for name in ("first_look", "top_ten_last_week", "big_orders_pune_nagpur"):
            self.assertEqual(run(con, name), [], "%s on an empty table should return no rows" % name)

    def test_edges_of_last_week_and_cancelled(self):
        rows = [
            row(1, "2026-10-18", "Pune", "delivered", 5000.0),   # Sunday before: out
            row(2, "2026-10-19", "Pune", "delivered", 100.0),    # Monday: in
            row(3, "2026-10-25", "Nagpur", "delivered", 200.0),  # Sunday: in
            row(4, "2026-10-26", "Pune", "delivered", 6000.0),   # next Monday: out
            row(5, "2026-10-21", "Pune", "cancelled", 9000.0),   # cancelled: out
        ]
        self.compare(run(make_db(rows), "top_ten_last_week"),
                     [(3, "2026-10-25", "Nagpur", 200.0), (2, "2026-10-19", "Pune", 100.0)],
                     "only delivered orders from 19 to 25 October, both days included")

    def test_tie_on_amount(self):
        rows = [row(i, "2026-10-20", "Pune", "delivered", 1200.0) for i in (14, 12, 13, 11, 15, 16, 17, 18, 19, 20, 21)]
        got = run(make_db(rows), "top_ten_last_week")
        self.assertEqual([r[0] for r in got], list(range(11, 21)),
                         "11 orders share the same amount: break the tie with ORDER BY amount DESC, order_id")

    def test_and_or_brackets(self):
        rows = [
            row(1, "2026-10-20", "Pune", "delivered", 1000.0),   # in: exactly 1000
            row(2, "2026-10-20", "Pune", "delivered", 999.99),   # out: too small
            row(3, "2026-10-20", "Nagpur", "cancelled", 2000.0), # out: cancelled
            row(4, "2026-10-12", "Pune", "delivered", 2000.0),   # out: wrong week
            row(5, "2026-10-20", "Mumbai", "delivered", 2000.0), # out: wrong city
            row(6, "2026-10-20", "Nagpur", "delivered", 1500.0), # in
        ]
        self.compare(run(make_db(rows), "big_orders_pune_nagpur"), [(1, "Pune", 1000.0), (6, "Nagpur", 1500.0)],
                     "every condition must apply to both cities: put the OR inside brackets")


if __name__ == "__main__":
    unittest.main()
