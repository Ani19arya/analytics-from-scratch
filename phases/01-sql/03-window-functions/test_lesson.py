"""Tests for lesson 03: window functions.

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




class TestWindows(SqlTestCase):
    def setUp(self):
        self.revenue = sorted(read_csv("monthly_revenue"), key=lambda r: (r["region"], r["month"]))
        self.reps = read_csv("rep_sales")

    def test_running_total(self):
        expected, running, last_region = [], 0, None
        for r in self.revenue:
            if r["region"] != last_region:
                running, last_region = 0, r["region"]
            running += r["revenue"]
            expected.append((r["region"], r["month"], r["revenue"], running))
        self.assertRowsEqual(self.run_query("running_total"), expected)

    def ranked(self):
        out = []
        for region in sorted({r["region"] for r in self.reps}):
            group = sorted((r for r in self.reps if r["region"] == region), key=lambda r: (-r["sales"], r["rep"]))
            for i, r in enumerate(group):
                rank = 1 + sum(1 for o in group if o["sales"] > r["sales"])
                out.append((region, r["rep"], r["sales"], rank, i + 1))
        return out

    def test_rep_rank(self):
        expected = self.ranked()
        self.assertTrue(any(a[3] == b[3] for a, b in zip(expected, expected[1:]) if a[0] == b[0]), "data should contain a tie")
        self.assertRowsEqual(self.run_query("rep_rank"), expected)

    def test_top_reps_keeps_ties(self):
        expected = sorted((r[0], r[1]) for r in self.ranked() if r[3] == 1)
        self.assertRowsEqual(self.run_query("top_reps"), expected)

    def test_month_over_month(self):
        expected, prev, last_region = [], None, None
        for r in self.revenue:
            if r["region"] != last_region:
                prev, last_region = None, r["region"]
            change = None if prev is None else r["revenue"] - prev
            expected.append((r["region"], r["month"], r["revenue"], prev, change))
            prev = r["revenue"]
        self.assertRowsEqual(self.run_query("month_over_month"), expected)


if __name__ == "__main__":
    unittest.main()
