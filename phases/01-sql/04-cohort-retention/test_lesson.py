"""Tests for lesson 04: cohort retention.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

The expected answers are computed with plain Python sets and month arithmetic,
never with SQL. Your queries run on three kinds of data:
1. the committed data/*.csv,
2. a second dataset built in memory with make_data.build(seed=2026), with one
   user's signup-day event removed, so dividing by the month 0 actives instead
   of the cohort size fails, and typing out the answers cannot pass,
3. tiny hand-made tables for the edge cases: empty tables, a month where
   nobody came back (a real zero), a cohort that crosses the year end, repeat
   events in one month, and a cohort too young to have a month 1.
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

TABLES = {"users": ["user_id", "signup_date"], "events": ["user_id", "event_date"]}
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


def round1(x):
    """Round to 1 decimal, halves away from zero, the way SQLite's ROUND does (Python's round(31.25, 1) is 31.2)."""
    return math.floor(x * 10 + 0.5) / 10


def month_index(date_text):
    """2026-01-15 -> 2026 * 12 + 1. Two indexes subtract to a calendar month difference."""
    return int(date_text[:4]) * 12 + int(date_text[5:7])


# The reference answers.

def ref_cohort_sizes(d):
    sizes = {}
    for u in d["users"]:
        c = u["signup_date"][:7]
        sizes[c] = sizes.get(c, 0) + 1
    return sorted(sizes.items())


def ref_retention(d):
    if not d["events"]:
        return []
    data_end = max(month_index(e["event_date"]) for e in d["events"])
    signup = {u["user_id"]: u["signup_date"] for u in d["users"]}
    sizes = dict(ref_cohort_sizes(d))
    active = {}
    for e in d["events"]:
        uid = e["user_id"]
        if uid not in signup:
            continue
        k = (signup[uid][:7], month_index(e["event_date"]) - month_index(signup[uid]))
        active.setdefault(k, set()).add(uid)
    out = []
    for cohort, size in sorted(sizes.items()):
        observed = data_end - month_index(cohort + "-01")
        for m in range(0, observed + 1):  # every month the data can show, zeros included
            n = len(active.get((cohort, m), ()))
            out.append((cohort, m, n, size, round1(100.0 * n / size)))
    return out


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

    def assertRowsEqual(self, actual, expected, where, tol=0.051):
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
        self.assertRowsEqual(self.run_query(con, "cohort_sizes"), ref_cohort_sizes(d), where + ", cohort_sizes")
        self.assertRowsEqual(self.run_query(con, "retention"), ref_retention(d), where + ", retention")


class TestCommittedData(SqlTestCase):
    def setUp(self):
        self.d = {t: read_csv(t) for t in TABLES}
        self.con = make_db(self.d)

    def test_cohort_sizes(self):
        self.assertRowsEqual(self.run_query(self.con, "cohort_sizes"), ref_cohort_sizes(self.d), "cohort_sizes")

    def test_retention_table(self):
        self.assertRowsEqual(self.run_query(self.con, "retention"), ref_retention(self.d), "retention")

    def test_month_zero_is_everyone(self):
        # True here only because every user has an event on their signup day.
        actual = self.run_query(self.con, "retention")
        zero = [r for r in actual if r[1] == 0]
        self.assertEqual(len(zero), len(ref_cohort_sizes(self.d)), "need a month 0 row for every cohort")
        for r in zero:
            self.assertEqual(r[2], r[3], "month 0 should include every user in cohort %s: count DISTINCT users" % r[0])


class TestSecondDataset(SqlTestCase):
    def test_same_queries_on_new_data(self):
        d = {t: as_loaded(rows) for t, rows in make_data.build(seed=SECOND_SEED).items()}
        first = d["users"][0]
        d["events"] = [e for e in d["events"] if not (e["user_id"] == first["user_id"] and e["event_date"] == first["signup_date"])]
        self.check_all(d, "second dataset (seed %d, user %s has no signup-day event): divide by the cohort size from "
                          "users, not by the month 0 actives" % (SECOND_SEED, first["user_id"]))


def user(uid, day):
    return {"user_id": uid, "signup_date": day}


def event(uid, day):
    return {"user_id": uid, "event_date": day}


class TestEdgeCases(SqlTestCase):
    def test_empty_tables(self):
        self.check_all({"users": [], "events": []}, "empty tables (both queries should return no rows)")

    def test_real_zero_month(self):
        d = {
            "users": [user(1, "2026-01-05"), user(2, "2026-01-20"), user(3, "2026-02-10")],
            "events": [event(1, "2026-01-05"), event(2, "2026-01-20"), event(3, "2026-02-10"), event(1, "2026-03-02")],
        }
        self.check_all(d, "nobody from 2026-01 was active in month 1 (February) but user 1 came back in March: "
                          "month 1 needs a row with active_users 0 and retention_pct 0.0, not a missing row")

    def test_year_end_and_repeat_events(self):
        d = {
            "users": [user(1, "2025-12-31"), user(2, "2025-12-01"), user(3, "2026-01-10")],
            "events": [event(1, "2025-12-31"), event(2, "2025-12-01"), event(3, "2026-01-10"),
                       event(1, "2026-01-01"), event(1, "2026-01-15"), event(1, "2026-01-28")],
        }
        self.check_all(d, "user 1 signed up 31 Dec 2025 and came back three times in January 2026: that is ONE "
                          "active user in month 1 (not -11, and not 3)")

    def test_young_cohort(self):
        d = {
            "users": [user(1, "2026-05-03"), user(2, "2026-06-10")],
            "events": [event(1, "2026-05-03"), event(2, "2026-06-10"), event(1, "2026-06-12")],
        }
        self.check_all(d, "the data ends in June, so the 2026-06 cohort has only a month 0 row")


if __name__ == "__main__":
    unittest.main()
