"""Tests for lesson 02: SQL interview questions.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql
"""
import csv
import datetime
import os
import re
import sqlite3
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if os.environ.get("CHECK_SOLUTION") == "1":
    SQL_FILE = os.path.join(HERE, "solution", "solution.sql")
else:
    SQL_FILE = os.path.join(HERE, "exercise.sql")

TABLES = {
    "employees": [("emp_id", int), ("name", str), ("department", str), ("salary", int)],
    "signups": [("signup_id", int), ("email", str), ("signed_up_at", str)],
    "logins": [("user_id", int), ("login_date", str)],
    "orders": [("order_id", int), ("order_date", str), ("amount", float)],
}


def read(table):
    cols = TABLES[table]
    with open(os.path.join(HERE, "data", table + ".csv"), newline="") as f:
        return [tuple(t(r[c]) for c, t in cols) for r in csv.DictReader(f)]


def load_db():
    con = sqlite3.connect(":memory:")
    for table, cols in TABLES.items():
        types = {int: "INTEGER", str: "TEXT", float: "REAL"}
        con.execute("CREATE TABLE %s (%s)" % (table, ", ".join("%s %s" % (c, types[t]) for c, t in cols)))
        con.executemany("INSERT INTO %s VALUES (%s)" % (table, ",".join("?" * len(cols))), read(table))
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


class TestInterviewQueries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.con = load_db()
        cls.queries = load_queries(SQL_FILE)

    def run_query(self, name):
        sql = self.queries.get(name, "")
        if not sql:
            self.fail("query '%s' is empty in %s: write it first" % (name, os.path.basename(SQL_FILE)))
        return [tuple(r) for r in self.con.execute(sql).fetchall()]

    def assertRows(self, actual, expected):
        self.assertEqual(len(actual), len(expected), "got %d rows, expected %d" % (len(actual), len(expected)))
        for a, e in zip(actual, expected):
            self.assertEqual(len(a), len(e), "row %r, expected %r" % (a, e))
            for x, y in zip(a, e):
                if isinstance(y, float):
                    self.assertIsNotNone(x, "row %r, expected %r" % (a, e))
                    self.assertAlmostEqual(x, y, delta=0.051, msg="row %r, expected %r" % (a, e))
                else:
                    self.assertEqual(x, y, "row %r, expected %r" % (a, e))

    def test_second_highest_salary(self):
        distinct = sorted({r[3] for r in read("employees")}, reverse=True)
        self.assertRows(self.run_query("second_highest_salary"), [(distinct[1],)])

    def test_duplicate_emails(self):
        c = {}
        for _, e, _ in read("signups"):
            k = e.strip().lower()
            c[k] = c.get(k, 0) + 1
        expected = sorted([(k, n) for k, n in c.items() if n > 1], key=lambda x: (-x[1], x[0]))
        self.assertRows(self.run_query("duplicate_emails"), expected)

    def test_three_day_streaks(self):
        days = {}
        for u, d in read("logins"):
            days.setdefault(u, set()).add(datetime.date.fromisoformat(d))
        expected = []
        for u in sorted(days):
            best = run = 0
            prev = None
            for d in sorted(days[u]):
                run = run + 1 if prev and (d - prev).days == 1 else 1
                best = max(best, run)
                prev = d
            if best >= 3:
                expected.append((u, best))
        got = self.run_query("three_day_streaks")
        self.assertNotIn(41, [r[0] for r in got], "user 41 logs in twice a day: count distinct days")
        self.assertRows(got, expected)

    def test_top_two_per_department(self):
        by = {}
        for _, name, dept, sal in read("employees"):
            by.setdefault(dept, []).append((name, sal))
        expected = []
        for dept in sorted(by):
            levels = sorted({s for _, s in by[dept]}, reverse=True)[:2]
            rows = [(dept, n, s, levels.index(s) + 1) for n, s in by[dept] if s in levels]
            expected += sorted(rows, key=lambda r: (r[3], r[1]))
        self.assertRows(self.run_query("top_two_per_department"), expected)

    def test_running_total(self):
        daily = {}
        for _, d, amt in read("orders"):
            if d.startswith("2026-09"):
                daily[d] = daily.get(d, 0) + amt
        expected, total = [], 0.0
        for d in sorted(daily):
            total += round(daily[d], 2)
            expected.append((d, round(daily[d], 2), round(total, 2)))
        self.assertRows(self.run_query("running_total"), expected)

    def test_month_over_month(self):
        rev = {}
        for _, d, amt in read("orders"):
            rev[d[:7]] = rev.get(d[:7], 0) + amt
        months = ["2026-%02d" % m for m in range(1, 10)]
        expected, prev = [], None
        for m in months:
            r = round(rev.get(m, 0), 2)
            pct = None if not prev else round(100.0 * (r - prev) / prev, 1)
            expected.append((m, r, prev, pct))
            prev = r
        got = self.run_query("month_over_month")
        self.assertIn("2026-04", [g[0] for g in got], "April had no orders but must still appear, with revenue 0")
        self.assertEqual(len(got), len(expected))
        for g, e in zip(got, expected):
            self.assertEqual(g[0], e[0])
            for x, y in zip(g[1:], e[1:]):
                if y is None:
                    self.assertIsNone(x, "row %r, expected %r" % (g, e))
                else:
                    self.assertAlmostEqual(x, y, delta=0.051, msg="row %r, expected %r" % (g, e))


if __name__ == "__main__":
    unittest.main()
