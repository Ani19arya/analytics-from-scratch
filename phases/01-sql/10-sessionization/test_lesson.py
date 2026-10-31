"""Tests for lesson 10: sessionization from raw events.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

The expected answers are computed with plain Python datetime arithmetic,
never with SQL. Your queries run on three kinds of data:
1. the committed data/events.csv,
2. a second dataset built in memory with make_data.build(seed=2026), so a
   query that just types out the answers cannot pass,
3. tiny hand-made tables for the edge cases: no events, one event, a pause
   of exactly 1800 seconds (same session) and of 1801 seconds (new session),
   two events in the same second, a visit that runs past midnight, two users
   whose events interleave, and an event with no time (NULL).
"""
import csv
import datetime
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

TABLES = {"events": ["event_id", "user_id", "event_time", "event_name"]}
SECOND_SEED = 2026
TIMEOUT = 1800


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
    """Round to 1 decimal, halves away from zero, the way SQLite's ROUND does."""
    return math.floor(x * 10 + 0.5) / 10


# The reference answers, in plain Python.

def parse(stamp):
    return datetime.datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")


def ref_sessionized_events(d):
    """[(event_id, user_id, event_time, gap_seconds, session_number)] in user, time, event_id order."""
    by_user = {}
    for e in d["events"]:
        if e["event_time"] is not None:
            by_user.setdefault(e["user_id"], []).append(e)
    out = []
    for user in sorted(by_user):
        prev, session = None, 0
        for e in sorted(by_user[user], key=lambda e: (e["event_time"], e["event_id"])):
            t = parse(e["event_time"])
            gap = None if prev is None else int((t - prev).total_seconds())
            if gap is None or gap > TIMEOUT:
                session += 1
            out.append((e["event_id"], user, e["event_time"], gap, session))
            prev = t
    return out


def ref_sessions(d):
    groups = {}
    for event_id, user, stamp, gap, session in ref_sessionized_events(d):
        groups.setdefault((user, session), []).append(stamp)
    out = []
    for (user, session), stamps in sorted(groups.items()):
        out.append((user, session, stamps[0], stamps[-1], len(stamps),
                    int((parse(stamps[-1]) - parse(stamps[0])).total_seconds())))
    return out


def ref_user_summary(d):
    per_user = {}
    for user, session, start, end, events, duration in ref_sessions(d):
        s = per_user.setdefault(user, [0, 0, 0])
        s[0] += 1
        s[1] += events
        s[2] += duration
    return [(u, n, ev, round1(total / n)) for u, (n, ev, total) in sorted(per_user.items())]


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
            "%s: got %d rows, expected %d. Expected rows start %r" % (where, len(actual), len(expected), expected[:4]),
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
        self.assertRowsEqual(self.run_query(con, "sessionized_events"), ref_sessionized_events(d),
                             where + ", sessionized_events")
        self.assertRowsEqual(self.run_query(con, "sessions"), ref_sessions(d), where + ", sessions")
        self.assertRowsEqual(self.run_query(con, "user_summary"), ref_user_summary(d), where + ", user_summary")


class TestCommittedData(SqlTestCase):
    def setUp(self):
        self.d = read_csv_all()
        self.con = make_db(self.d)

    def test_sessionized_events(self):
        got = self.run_query(self.con, "sessionized_events")
        timed = sum(1 for e in self.d["events"] if e["event_time"] is not None)
        self.assertEqual(len(got), timed,
                         "sessionized_events should have one row per event that has a time (%d), and leave out "
                         "the events with no event_time" % timed)
        self.assertRowsEqual(got, ref_sessionized_events(self.d),
                             "sessionized_events (gap in whole seconds; a new session only when the gap is MORE "
                             "than 1800)")

    def test_sessions(self):
        got = self.run_query(self.con, "sessions")
        exact = sum(1 for r in ref_sessionized_events(self.d) if r[3] == TIMEOUT)
        self.assertEqual(len(got), len(ref_sessions(self.d)),
                         "the data has %d pauses of exactly 1800 seconds, which stay inside a session; compare "
                         "whole seconds, not julianday() * 86400" % exact)
        self.assertRowsEqual(got, ref_sessions(self.d), "sessions")

    def test_user_summary(self):
        self.assertRowsEqual(self.run_query(self.con, "user_summary"), ref_user_summary(self.d), "user_summary")


def read_csv_all():
    return {t: read_csv(t) for t in TABLES}


class TestSecondDataset(SqlTestCase):
    def test_same_queries_on_new_data(self):
        d = {t: as_loaded(rows) for t, rows in make_data.build(seed=SECOND_SEED).items()}
        self.check_all(d, "second dataset (seed %d)" % SECOND_SEED)


def events(spec):
    """spec: list of (user_id, event_time) -> event rows, event_id in list order."""
    return {"events": [{"event_id": n, "user_id": u, "event_time": t, "event_name": "play_video"}
                       for n, (u, t) in enumerate(spec, 1)]}


class TestEdgeCases(SqlTestCase):
    def test_empty_table(self):
        self.check_all({"events": []}, "no events (every query returns no rows)")

    def test_one_event(self):
        self.check_all(events([("A", "2026-10-12 09:00:00")]),
                       "one event is one session of 0 seconds, and its gap is NULL")

    def test_boundary_1800_and_1801(self):
        d = events([("A", "2026-10-13 10:05:49"), ("A", "2026-10-13 10:35:49"),
                    ("A", "2026-10-13 11:05:50")])
        self.check_all(d, "a pause of exactly 1800 seconds (10:05:49 to 10:35:49) stays in session 1, a pause of "
                          "1801 seconds starts session 2; julianday() * 86400 turns this 1800 into 1800.00001")

    def test_same_second(self):
        d = {"events": [{"event_id": 7, "user_id": "A", "event_time": "2026-10-12 09:00:00", "event_name": "x"},
                        {"event_id": 3, "user_id": "A", "event_time": "2026-10-12 09:00:00", "event_name": "y"},
                        {"event_id": 9, "user_id": "A", "event_time": "2026-10-12 09:10:00", "event_name": "z"}]}
        self.check_all(d, "two events in the same second: order by event_time, then event_id, so event 3 comes "
                          "first and event 7 has a gap of 0")

    def test_past_midnight(self):
        d = events([("A", "2026-10-14 23:50:00"), ("A", "2026-10-15 00:10:00"), ("A", "2026-10-15 00:20:00")])
        self.check_all(d, "a visit from 23:50 to 00:20 is one session of 1800 seconds: do not split sessions "
                          "by date")

    def test_interleaved_users(self):
        d = events([("A", "2026-10-12 09:00:00"), ("B", "2026-10-12 09:05:00"), ("A", "2026-10-12 09:50:00"),
                    ("B", "2026-10-12 09:20:00")])
        self.check_all(d, "A has a 50-minute pause (2 sessions) and B a 15-minute one (1 session): LAG needs "
                          "PARTITION BY user_id, or A's gap is measured from B's event")

    def test_null_time(self):
        d = events([("A", "2026-10-12 09:00:00"), ("A", None), ("A", "2026-10-12 09:20:00"), ("C", None)])
        self.check_all(d, "events with no event_time are left out: A has one session of 2 events, and C, who "
                          "only has a NULL time, has no session at all")


if __name__ == "__main__":
    unittest.main()
