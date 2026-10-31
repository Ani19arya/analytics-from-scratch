"""Tests for lesson 02: SQL interview questions.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

Every expected answer is computed in plain Python below, on three kinds of data: the
committed CSVs, a second dataset built in memory with another seed, and tiny hand-made
tables for the edge cases (a tie, one salary, a zero month, duplicate days).
"""
import csv
import datetime
import os
import re
import sqlite3
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if os.environ.get("CHECK_SOLUTION") == "1":
    SQL_FILE = os.path.join(HERE, "solution", "solution.sql")
else:
    SQL_FILE = os.path.join(HERE, "exercise.sql")

sys.path.insert(0, HERE)
import make_data  # noqa: E402

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


def committed():
    return {t: read(t) for t in TABLES}


def make_db(data):
    """An in-memory database with the four tables. data is {table: rows}; missing tables are empty."""
    con = sqlite3.connect(":memory:")
    types = {int: "INTEGER", str: "TEXT", float: "REAL"}
    for table, cols in TABLES.items():
        con.execute("CREATE TABLE %s (%s)" % (table, ", ".join("%s %s" % (c, types[t]) for c, t in cols)))
        rows = [tuple(t(v) for (_, t), v in zip(cols, r)) for r in data.get(table, [])]
        con.executemany("INSERT INTO %s VALUES (%s)" % (table, ",".join("?" * len(cols))), rows)
    return con


def load_db():
    """The committed data, for trying queries by hand."""
    return make_db(committed())


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


# ---- plain Python references -------------------------------------------------

def ref_second_highest(data):
    distinct = sorted({r[3] for r in data["employees"]}, reverse=True)
    return [(distinct[1] if len(distinct) > 1 else None,)]


def ref_duplicate_emails(data):
    c = {}
    for _, e, _ in data["signups"]:
        k = e.strip().lower()
        c[k] = c.get(k, 0) + 1
    return sorted([(k, n) for k, n in c.items() if n > 1], key=lambda x: (-x[1], x[0]))


def ref_streaks(data):
    days = {}
    for u, d in data["logins"]:
        days.setdefault(u, set()).add(datetime.date.fromisoformat(d))
    out = []
    for u in sorted(days):
        best = run = 0
        prev = None
        for d in sorted(days[u]):
            run = run + 1 if prev and (d - prev).days == 1 else 1
            best = max(best, run)
            prev = d
        if best >= 3:
            out.append((u, best))
    return out


def ref_top_two(data):
    by = {}
    for _, name, dept, sal in data["employees"]:
        by.setdefault(dept, []).append((name, sal))
    out = []
    for dept in sorted(by):
        levels = sorted({s for _, s in by[dept]}, reverse=True)[:2]
        rows = [(dept, n, s, levels.index(s) + 1) for n, s in by[dept] if s in levels]
        out += sorted(rows, key=lambda r: (r[3], r[1]))
    return out


def ref_running_total(data):
    daily = {}
    for _, d, amt in data["orders"]:
        if d.startswith("2026-09"):
            daily[d] = daily.get(d, 0) + amt
    out, total = [], 0.0
    for d in sorted(daily):
        total += round(daily[d], 2)
        out.append((d, round(daily[d], 2), round(total, 2)))
    return out


def ref_month_over_month(data):
    rev = {}
    for _, d, amt in data["orders"]:
        rev[d[:7]] = rev.get(d[:7], 0) + amt
    first, last = min(rev), max(rev)
    months, (y, m) = [], (int(first[:4]), int(first[5:]))
    while "%d-%02d" % (y, m) <= last:
        months.append("%d-%02d" % (y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    out, prev = [], None
    for mo in months:
        r = round(rev.get(mo, 0), 2)
        pct = None if not prev else round(100.0 * (r - prev) / prev, 1)
        out.append((mo, r, prev, pct))
        prev = r
    return out


# ---- the checks ---------------------------------------------------------------

class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.queries = load_queries(SQL_FILE)

    def run_query(self, name, con):
        sql = self.queries.get(name, "")
        if not sql:
            self.fail("query '%s' is empty in %s: write it first" % (name, os.path.basename(SQL_FILE)))
        return [tuple(r) for r in con.execute(sql).fetchall()]

    def assertRows(self, actual, expected, where):
        self.assertEqual(len(actual), len(expected), "%s: got %d rows, expected %d" % (where, len(actual), len(expected)))
        for a, e in zip(actual, expected):
            self.assertEqual(len(a), len(e), "%s: row %r, expected %r" % (where, a, e))
            for x, y in zip(a, e):
                if y is None:
                    self.assertIsNone(x, "%s: row %r, expected %r (NULL)" % (where, a, e))
                elif isinstance(y, float):
                    self.assertIsNotNone(x, "%s: row %r, expected %r" % (where, a, e))
                    self.assertAlmostEqual(x, y, delta=0.051, msg="%s: row %r, expected %r" % (where, a, e))
                else:
                    self.assertEqual(x, y, "%s: row %r, expected %r" % (where, a, e))

    def check_all(self, data, where):
        con = make_db(data)
        self.assertRows(self.run_query("second_highest_salary", con), ref_second_highest(data), where + ", second_highest_salary")
        self.assertRows(self.run_query("duplicate_emails", con), ref_duplicate_emails(data), where + ", duplicate_emails")
        self.assertRows(self.run_query("three_day_streaks", con), ref_streaks(data), where + ", three_day_streaks")
        self.assertRows(self.run_query("top_two_per_department", con), ref_top_two(data), where + ", top_two_per_department")
        self.assertRows(self.run_query("running_total", con), ref_running_total(data), where + ", running_total")
        got = self.run_query("month_over_month", con)
        self.assertIn("2026-04", [g[0] for g in got], "%s: April had no orders but must still appear, with revenue 0" % where)
        self.assertRows(got, ref_month_over_month(data), where + ", month_over_month")


class TestCommittedData(Base):
    def test_all_six_queries(self):
        data = committed()
        got = self.run_query("three_day_streaks", make_db(data))
        self.assertNotIn(41, [r[0] for r in got], "user 41 logs in twice a day on two days: count distinct days")
        self.check_all(data, "committed data")


class TestSecondDataset(Base):
    def test_all_six_queries(self):
        self.check_all(make_data.build(seed=7), "second dataset (seed 7)")


class TestEdgeCases(Base):
    def test_one_salary_gives_null(self):
        data = {"employees": [(1, "A", "Sales", 50000), (2, "B", "Sales", 50000)]}
        self.assertRows(self.run_query("second_highest_salary", make_db(data)), [(None,)],
                        "everyone earns the same, so there is no second highest: expect NULL")

    def test_second_highest_with_tie_at_top(self):
        data = {"employees": [(1, "A", "Sales", 90), (2, "B", "Sales", 90), (3, "C", "Sales", 80)]}
        self.assertRows(self.run_query("second_highest_salary", make_db(data)), [(80,)],
                        "two people share the top salary: the second highest distinct value is 80")

    def test_no_duplicates(self):
        data = {"signups": [(1, "a@example.com", "2026-09-01 08:00"), (2, "b@example.com", "2026-09-01 09:00")]}
        self.assertRows(self.run_query("duplicate_emails", make_db(data)), [], "no email repeats: expect no rows")

    def test_streak_with_duplicate_days(self):
        logins = [(1, "2026-10-05"), (1, "2026-10-06"), (1, "2026-10-08"), (1, "2026-10-08"),
                  (2, "2026-10-01"), (2, "2026-10-02"), (2, "2026-10-02"), (2, "2026-10-03")]
        data = {"logins": logins}
        self.assertRows(self.run_query("three_day_streaks", make_db(data)), ref_streaks(data),
                        "user 1 has no 3 day run (the 7th is missing); user 2 has 3 days with a repeat")

    def test_top_two_with_ties(self):
        emps = [(1, "A", "Ops", 100), (2, "B", "Ops", 100), (3, "C", "Ops", 90), (4, "D", "Ops", 90), (5, "E", "Ops", 80)]
        data = {"employees": emps}
        self.assertRows(self.run_query("top_two_per_department", make_db(data)), ref_top_two(data),
                        "ties share a level: two people at 100 and two at 90, nobody at 80")

    def test_running_total_single_day(self):
        data = {"orders": [(1, "2026-09-03", 10.0), (2, "2026-09-03", 5.5), (3, "2026-08-30", 99.0)]}
        self.assertRows(self.run_query("running_total", make_db(data)), [("2026-09-03", 15.5, 15.5)],
                        "one day in September: one row; the August order is outside the window")

    def test_month_after_a_zero_month(self):
        orders = [(1, "2026-03-10", 100.0), (2, "2026-05-02", 50.0)]
        data = {"orders": orders}
        self.assertRows(self.run_query("month_over_month", make_db(data)), ref_month_over_month(data),
                        "April is 0, so April's change is -100.0 and May's change is NULL (growth from zero)")


if __name__ == "__main__":
    unittest.main()
