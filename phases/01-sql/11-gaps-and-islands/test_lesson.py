"""Tests for lesson 11: gaps and islands: streaks.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

The expected answers are computed with plain Python dates and sets, never
with SQL. Your queries run on three kinds of data:
1. the committed data/workouts.csv,
2. a second dataset built in memory with make_data.build(seed=2026), so a
   query that just types out the answers cannot pass,
3. tiny hand-made tables for the edge cases: no workouts, one workout, two
   and three workouts on the same day, a streak across the end of a month,
   two streaks of the same length (a tie), a one-day gap, and a workout with
   no time (NULL).
"""
import csv
import datetime
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

TABLES = {"workouts": ["workout_id", "user_id", "logged_at", "workout_type", "minutes"]}
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


# The reference answers, in plain Python.

def ref_streaks(d):
    """[(user_id, streak_start, streak_end, days)]: walk each user's sorted distinct days."""
    days = {}
    for w in d["workouts"]:
        if w["logged_at"] is not None:
            days.setdefault(w["user_id"], set()).add(datetime.date.fromisoformat(w["logged_at"][:10]))
    out = []
    for user in sorted(days):
        run = []
        for day in sorted(days[user]):
            if run and (day - run[-1]).days != 1:
                out.append((user, run[0].isoformat(), run[-1].isoformat(), len(run)))
                run = []
            run.append(day)
        out.append((user, run[0].isoformat(), run[-1].isoformat(), len(run)))
    return out


def ref_longest_streak(d):
    best = {}
    for user, start, end, n in ref_streaks(d):  # streaks come in start order, so ">" keeps the earlier of a tie
        if user not in best or n > best[user][0]:
            best[user] = (n, start, end)
    return [(u, n, s, e) for u, (n, s, e) in sorted(best.items())]


def ref_three_day_users(d):
    counts = {}
    for user, start, end, n in ref_streaks(d):
        if n >= 3:
            counts[user] = counts.get(user, 0) + 1
    return sorted(counts.items())


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

    def assertRowsEqual(self, actual, expected, where):
        self.assertEqual(
            len(actual), len(expected),
            "%s: got %d rows, expected %d. Expected rows start %r" % (where, len(actual), len(expected), expected[:4]),
        )
        for a, e in zip(actual, expected):
            self.assertEqual(tuple(a), tuple(e), "%s: row %r, expected %r" % (where, a, e))

    def check_all(self, d, where):
        con = make_db(d)
        self.assertRowsEqual(self.run_query(con, "streaks"), ref_streaks(d), where + ", streaks")
        self.assertRowsEqual(self.run_query(con, "longest_streak"), ref_longest_streak(d), where + ", longest_streak")
        self.assertRowsEqual(self.run_query(con, "three_day_users"), ref_three_day_users(d),
                             where + ", three_day_users")


class TestCommittedData(SqlTestCase):
    def setUp(self):
        self.d = {t: read_csv(t) for t in TABLES}
        self.con = make_db(self.d)

    def test_streaks(self):
        got = self.run_query(self.con, "streaks")
        workout_days = len({(w["user_id"], w["logged_at"][:10]) for w in self.d["workouts"] if w["logged_at"]})
        self.assertEqual(sum(r[3] for r in got), workout_days,
                         "the streak lengths should add up to the %d distinct (user, day) pairs: cut the logs down "
                         "to one row per user and day before ROW_NUMBER" % workout_days)
        self.assertRowsEqual(got, ref_streaks(self.d), "streaks")

    def test_longest_streak(self):
        self.assertRowsEqual(self.run_query(self.con, "longest_streak"), ref_longest_streak(self.d),
                             "longest_streak (on a tie, keep the earlier streak)")

    def test_three_day_users(self):
        self.assertRowsEqual(self.run_query(self.con, "three_day_users"), ref_three_day_users(self.d),
                             "three_day_users (streaks of 3 days or more)")


class TestSecondDataset(SqlTestCase):
    def test_same_queries_on_new_data(self):
        d = {t: as_loaded(rows) for t, rows in make_data.build(seed=SECOND_SEED).items()}
        self.check_all(d, "second dataset (seed %d)" % SECOND_SEED)


def logs(spec):
    """spec: list of (user_id, logged_at) -> workout rows, workout_id in list order."""
    return {"workouts": [{"workout_id": n, "user_id": u, "logged_at": t, "workout_type": "run", "minutes": 30}
                         for n, (u, t) in enumerate(spec, 1)]}


class TestEdgeCases(SqlTestCase):
    def test_empty_table(self):
        self.check_all({"workouts": []}, "no workouts (every query returns no rows)")

    def test_one_workout(self):
        self.check_all(logs([("A", "2026-10-05 07:00:00")]),
                       "one workout is one streak of 1 day; A is not a three-day user")

    def test_several_logs_on_one_day(self):
        d = logs([("A", "2026-10-01 07:00:00"), ("A", "2026-10-02 07:00:00"), ("A", "2026-10-02 07:00:04"),
                  ("A", "2026-10-02 19:30:00"), ("A", "2026-10-03 08:00:00")])
        self.check_all(d, "three logs on 2 October are one workout day: A has one streak of 3 days, 1 to 3 "
                          "October, not two short streaks")

    def test_across_month_end(self):
        d = logs([("A", "2026-09-29 07:00:00"), ("A", "2026-09-30 23:59:00"), ("A", "2026-10-01 00:01:00")])
        self.check_all(d, "29 September, 30 September and 1 October are three days in a row: use date "
                          "arithmetic, not the day-of-month number")

    def test_tie_for_longest(self):
        d = logs([("A", "2026-10-10 07:00:00"), ("A", "2026-10-11 07:00:00"),
                  ("A", "2026-10-03 07:00:00"), ("A", "2026-10-04 07:00:00"), ("A", "2026-10-07 07:00:00")])
        self.check_all(d, "A has two 2-day streaks (3 to 4 and 10 to 11 October): the longest is the earlier one")

    def test_one_day_gap(self):
        d = logs([("A", "2026-10-01 07:00:00"), ("A", "2026-10-02 07:00:00"), ("A", "2026-10-04 07:00:00"),
                  ("A", "2026-10-05 07:00:00"), ("A", "2026-10-06 07:00:00"), ("B", "2026-10-03 07:00:00")])
        self.check_all(d, "a rest day on 3 October ends A's streak: 1 to 2 October, then 4 to 6 October; B's "
                          "workout that day does not fill A's gap")

    def test_null_time(self):
        d = logs([("A", "2026-10-01 07:00:00"), ("A", None), ("A", "2026-10-02 07:00:00"), ("C", None)])
        self.check_all(d, "workouts with no logged_at are left out: A has one 2-day streak and C has no streak")


if __name__ == "__main__":
    unittest.main()
