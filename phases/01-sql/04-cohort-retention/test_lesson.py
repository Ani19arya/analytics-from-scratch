"""Tests for lesson 04: cohort retention.

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




def month_index(date_text):
    return int(date_text[:4]) * 12 + int(date_text[5:7])


class TestCohorts(SqlTestCase):
    def setUp(self):
        self.users = read_csv("users")
        self.events = read_csv("events")
        self.cohort = {u["user_id"]: u["signup_date"][:7] for u in self.users}
        self.signup = {u["user_id"]: u["signup_date"] for u in self.users}
        self.sizes = {}
        for c in self.cohort.values():
            self.sizes[c] = self.sizes.get(c, 0) + 1

    def test_cohort_sizes(self):
        self.assertRowsEqual(self.run_query("cohort_sizes"), sorted(self.sizes.items()))

    def expected_retention(self):
        active = {}
        for e in self.events:
            uid = e["user_id"]
            k = (self.cohort[uid], month_index(e["event_date"]) - month_index(self.signup[uid]))
            active.setdefault(k, set()).add(uid)
        return [
            (c, m, len(ids), self.sizes[c], round(100.0 * len(ids) / self.sizes[c], 1))
            for (c, m), ids in sorted(active.items())
        ]

    def test_retention_table(self):
        expected = self.expected_retention()
        actual = self.run_query("retention")
        self.assertRowsEqual(actual, expected, tol=0.051)

    def test_month_zero_is_everyone(self):
        actual = self.run_query("retention")
        zero = [r for r in actual if r[1] == 0]
        self.assertEqual(len(zero), len(self.sizes), "need a month 0 row for every cohort")
        for r in zero:
            self.assertEqual(r[2], r[3], "month 0 should include every user in cohort %s: count DISTINCT users" % r[0])


if __name__ == "__main__":
    unittest.main()
