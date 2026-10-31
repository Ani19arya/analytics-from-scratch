"""Tests for lesson 02: funnel conversion.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

Expected answers are computed here in plain Python from the raw events. The queries
run on the committed data, on a second dataset built with another seed, and on
small hand-made event logs (a tie, a NULL time, zero purchases, an empty table).
"""
import csv
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
STEPS = ["view_course", "add_to_cart", "begin_checkout", "purchase"]
OTHER_SEED = 5

sys.path.insert(0, HERE)
import make_data  # noqa: E402


def read_events():
    with open(os.path.join(HERE, "data", "events.csv"), newline="") as f:
        return [(int(r["user_id"]), r["event_name"], r["event_time"]) for r in csv.DictReader(f)]


def other_events():
    return [(r["user_id"], r["event_name"], r["event_time"]) for r in make_data.build(seed=OTHER_SEED)["events"]]


def make_db(events):
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE events (user_id, event_name, event_time)")
    con.executemany("INSERT INTO events VALUES (?, ?, ?)", events)
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


def expected_events_per_step(events):
    ev, us = {}, {}
    for uid, name, _ in events:
        ev[name] = ev.get(name, 0) + 1
        us.setdefault(name, set()).add(uid)
    return [(s, ev[s], len(us[s])) for s in STEPS if s in ev]


def expected_funnel(events):
    firsts = {}
    for uid, name, t in events:
        if t is None:
            continue
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


def expected_biggest_drop(events):
    f = expected_funnel(events)
    worst = min(range(1, 4), key=lambda i: (f[i][3], i))
    return [(f[worst - 1][1], f[worst][1], f[worst - 1][2] - f[worst][2], f[worst][3])]


class SqlTestCase(unittest.TestCase):
    queries = load_queries(SQL_FILE)

    def run_query(self, name, con):
        sql = self.queries.get(name, "")
        if not sql:
            self.fail("query '%s' is empty in %s: write it first" % (name, os.path.basename(SQL_FILE)))
        return [tuple(r) for r in con.execute(sql).fetchall()]

    def assertRowsEqual(self, actual, expected, tol=0.051, where=""):
        self.assertEqual(len(actual), len(expected), "%swrong number of rows: got %d, expected %d" % (where, len(actual), len(expected)))
        for a, e in zip(actual, expected):
            self.assertEqual(len(a), len(e), "%swrong number of columns in row %r, expected %r" % (where, a, e))
            for x, y in zip(a, e):
                if isinstance(y, float):
                    self.assertIsNotNone(x, "%sgot NULL where %r was expected" % (where, e))
                    self.assertAlmostEqual(x, y, delta=tol, msg="%srow %r, expected %r" % (where, a, e))
                else:
                    self.assertEqual(x, y, "%srow %r, expected %r" % (where, a, e))


class FunnelChecks:
    """The same checks, run once per dataset."""

    def test_events_per_step(self):
        self.assertRowsEqual(self.run_query("events_per_step", self.con), expected_events_per_step(self.events), where=self.where)

    def test_funnel(self):
        self.assertRowsEqual(self.run_query("funnel", self.con), expected_funnel(self.events), where=self.where)

    def test_counts_users_not_events(self):
        rows = self.run_query("funnel", self.con)
        n_users = len({e[0] for e in self.events})
        self.assertLessEqual(rows[0][2], n_users, "step 1 is more than the number of users: count DISTINCT users, not events")
        for a, b in zip(rows, rows[1:]):
            self.assertLessEqual(b[2], a[2], "a funnel can never grow from one step to the next")

    def test_biggest_drop(self):
        self.assertRowsEqual(self.run_query("biggest_drop", self.con), expected_biggest_drop(self.events), where=self.where)


class TestFunnel(FunnelChecks, SqlTestCase):
    where = "committed data: "

    @classmethod
    def setUpClass(cls):
        cls.events = read_events()
        cls.con = make_db(cls.events)


class TestFunnelSecondDataset(FunnelChecks, SqlTestCase):
    """A second dataset from make_data.build(seed=5), so a hard-coded VALUES list fails."""
    where = "second dataset (seed %d): " % OTHER_SEED

    @classmethod
    def setUpClass(cls):
        cls.events = other_events()
        cls.con = make_db(cls.events)


class TestHandMadeCases(SqlTestCase):
    def test_tie_goes_to_the_earlier_step(self):
        # 4 view, 2 add to cart, 1 checkout, 1 purchase: 50%, 50%, 100%.
        events = [(1, "view_course", "2026-10-01 09:00:00"), (2, "view_course", "2026-10-01 09:00:00"),
                  (3, "view_course", "2026-10-01 09:00:00"), (4, "view_course", "2026-10-01 09:00:00"),
                  (1, "add_to_cart", "2026-10-01 09:05:00"), (2, "add_to_cart", "2026-10-01 09:05:00"),
                  (1, "begin_checkout", "2026-10-01 09:10:00"), (1, "purchase", "2026-10-01 09:15:00")]
        got = self.run_query("biggest_drop", make_db(events))
        self.assertRowsEqual(got, [("view_course", "add_to_cart", 2, 50.0)],
                             where="tie between two steps at 50%: return the earlier transition. ")

    def test_null_time_and_out_of_order(self):
        events = [(1, "view_course", "2026-10-01 09:00:00"), (1, "add_to_cart", "2026-10-01 09:05:00"),
                  (2, "view_course", "2026-10-01 09:00:00"), (2, "add_to_cart", None),          # broken log line
                  (3, "view_course", "2026-10-02 09:00:00"), (3, "add_to_cart", "2026-10-01 08:00:00"),  # cart before view
                  (1, "begin_checkout", "2026-10-01 09:06:00")]
        got = self.run_query("funnel", make_db(events))
        self.assertRowsEqual(got, expected_funnel(events),
                             where="a NULL time is not a step, and a cart before the first view is not in order. ")

    def test_zero_purchases(self):
        events = [(1, "view_course", "2026-10-01 09:00:00"), (1, "add_to_cart", "2026-10-01 09:01:00"),
                  (1, "begin_checkout", "2026-10-01 09:02:00"), (2, "view_course", "2026-10-01 10:00:00")]
        con = make_db(events)
        self.assertRowsEqual(self.run_query("funnel", con), expected_funnel(events),
                             where="nobody purchased: the purchase step must still appear with 0 users. ")
        self.assertRowsEqual(self.run_query("biggest_drop", con), [("begin_checkout", "purchase", 1, 0.0)],
                             where="nobody purchased: ")

    def test_empty_table(self):
        self.assertEqual(self.run_query("events_per_step", make_db([])), [], "no events should give no rows")


if __name__ == "__main__":
    unittest.main()
