"""Tests for lesson 02: funnel conversion.

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
STEPS = ["view_course", "add_to_cart", "begin_checkout", "purchase"]


def read_events():
    with open(os.path.join(HERE, "data", "events.csv"), newline="") as f:
        return [(int(r["user_id"]), r["event_name"], r["event_time"]) for r in csv.DictReader(f)]


def load_db():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE events (user_id, event_name, event_time)")
    con.executemany("INSERT INTO events VALUES (?, ?, ?)", read_events())
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


def expected_funnel():
    firsts = {}
    for uid, name, t in read_events():
        d = firsts.setdefault(uid, {})
        if name not in d or t < d[name]:
            d[name] = t
    counts = [0, 0, 0, 0]
    for d in firsts.values():
        prev = None
        for i, step in enumerate(STEPS):
            t = d.get(step)
            if t is None or (prev is not None and t < prev):
                break
            counts[i] += 1
            prev = t
    rows = []
    for i, step in enumerate(STEPS):
        prev = counts[i - 1] if i else counts[0]
        rows.append((i + 1, step, counts[i], round(100.0 * counts[i] / prev, 1), round(100.0 * counts[i] / counts[0], 1)))
    return rows


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

    def assertRowsEqual(self, actual, expected, tol=0.051):
        self.assertEqual(len(actual), len(expected), "wrong number of rows: got %d, expected %d" % (len(actual), len(expected)))
        for a, e in zip(actual, expected):
            self.assertEqual(len(a), len(e), "wrong number of columns in row %r, expected %r" % (a, e))
            for x, y in zip(a, e):
                if isinstance(y, float):
                    self.assertIsNotNone(x, "got NULL where %r was expected" % (e,))
                    self.assertAlmostEqual(x, y, delta=tol, msg="row %r, expected %r" % (a, e))
                else:
                    self.assertEqual(x, y, "row %r, expected %r" % (a, e))


class TestFunnel(SqlTestCase):
    def test_events_per_step(self):
        ev, us = {}, {}
        for uid, name, _ in read_events():
            ev[name] = ev.get(name, 0) + 1
            us.setdefault(name, set()).add(uid)
        expected = [(s, ev[s], len(us[s])) for s in STEPS]
        self.assertRowsEqual(self.run_query("events_per_step"), expected)

    def test_funnel(self):
        self.assertRowsEqual(self.run_query("funnel"), expected_funnel())

    def test_counts_users_not_events(self):
        rows = self.run_query("funnel")
        self.assertLessEqual(rows[0][2], 435, "step 1 is more than the number of users: count DISTINCT users, not events")
        for a, b in zip(rows, rows[1:]):
            self.assertLessEqual(b[2], a[2], "a funnel can never grow from one step to the next")

    def test_biggest_drop(self):
        f = expected_funnel()
        worst = min(range(1, 4), key=lambda i: f[i][3])
        expected = [(f[worst - 1][1], f[worst][1], f[worst - 1][2] - f[worst][2], f[worst][3])]
        self.assertRowsEqual(self.run_query("biggest_drop"), expected)


if __name__ == "__main__":
    unittest.main()
