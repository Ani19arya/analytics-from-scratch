"""Tests for lesson 01: GROUP BY from raw rows.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

The expected answers are computed with a plain Python loop over the CSV,
so the test is also a second, independent way of doing GROUP BY.
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


def totals_by_hand(rows):
    """GROUP BY city, written as a loop: one bucket per key."""
    buckets = {}
    for row in rows:
        if row["status"] != "completed":
            continue
        b = buckets.setdefault(row["city"], {"orders": 0, "revenue": 0.0})
        b["orders"] += 1
        b["revenue"] += row["amount"]
    return buckets


class TestGroupBy(SqlTestCase):
    def test_status_counts(self):
        counts = {}
        for row in read_csv("orders"):
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        expected = sorted(counts.items())
        self.assertRowsEqual(self.run_query("status_counts"), expected)

    def test_city_totals(self):
        buckets = totals_by_hand(read_csv("orders"))
        expected = [
            (city, b["orders"], round(b["revenue"], 2), round(b["revenue"] / b["orders"], 2))
            for city, b in sorted(buckets.items())
        ]
        self.assertRowsEqual(self.run_query("city_totals"), expected)

    def test_busy_cities_uses_having(self):
        buckets = totals_by_hand(read_csv("orders"))
        kept = [(c, b["orders"], round(b["revenue"], 2)) for c, b in buckets.items() if b["orders"] >= 70]
        expected = sorted(kept, key=lambda r: -r[2])
        self.assertRowsEqual(self.run_query("busy_cities"), expected)


if __name__ == "__main__":
    unittest.main()
