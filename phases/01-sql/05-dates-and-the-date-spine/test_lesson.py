"""Tests for lesson 05: dates and the date spine.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

The expected answers are computed with Python's datetime module, never with
SQL. Your queries run on three kinds of data:
1. the committed data/*.csv,
2. a second dataset built in memory with make_data.build(seed=2026), so a
   query that just types out the answers cannot pass,
3. tiny hand-made tables for the edge cases: no signups at all, signups a
   second either side of IST midnight, zero days at the very start and end
   of the period, a period that crosses a month end and a year end, and a
   period of a single day.
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

TABLES = {"signups": ["user_id", "signed_up_at_utc"], "report_period": ["start_date", "end_date"]}
SECOND_SEED = 2026
IST = datetime.timedelta(hours=5, minutes=30)


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


def round2(x):
    """Round to 2 decimals, halves away from zero, the way SQLite's ROUND does."""
    return math.floor(x * 100 + 0.5) / 100


# The reference answers.

def ist_day(stamp):
    """'2026-09-01 18:30:00' in UTC -> '2026-09-02', the IST calendar day."""
    utc = datetime.datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")
    return (utc + IST).date().isoformat()


def period_days(d):
    """Every day from start_date to end_date, both included, by plain date arithmetic."""
    p = d["report_period"][0]
    day = datetime.date.fromisoformat(p["start_date"])
    end = datetime.date.fromisoformat(p["end_date"])
    out = []
    while day <= end:
        out.append(day.isoformat())
        day += datetime.timedelta(days=1)
    return out


def ref_daily_signups(d):
    counts = {}
    for s in d["signups"]:
        k = ist_day(s["signed_up_at_utc"])
        counts[k] = counts.get(k, 0) + 1
    return [(day, counts.get(day, 0)) for day in period_days(d)]


def ref_zero_days(d):
    return [(day,) for day, n in ref_daily_signups(d) if n == 0]


def ref_summary(d):
    daily = ref_daily_signups(d)
    total = sum(n for _, n in daily)
    return [(len(daily), total, round2(total / len(daily)))]


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

    def assertRowsEqual(self, actual, expected, where, tol=0.0051):
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
        self.assertRowsEqual(self.run_query(con, "daily_signups"), ref_daily_signups(d), where + ", daily_signups")
        self.assertRowsEqual(self.run_query(con, "zero_days"), ref_zero_days(d), where + ", zero_days")
        self.assertRowsEqual(self.run_query(con, "summary"), ref_summary(d), where + ", summary")


class TestCommittedData(SqlTestCase):
    def setUp(self):
        self.d = {t: read_csv(t) for t in TABLES}
        self.con = make_db(self.d)

    def test_one_row_per_day(self):
        got = self.run_query(self.con, "daily_signups")
        self.assertEqual(len(got), 30, "daily_signups should have one row for each of the 30 days of September, "
                                       "zero days included: build the days from report_period, not from signups")

    def test_daily_signups(self):
        self.assertRowsEqual(self.run_query(self.con, "daily_signups"), ref_daily_signups(self.d),
                             "daily_signups (days are IST: add 5 hours 30 minutes to the UTC time before taking the date)")

    def test_zero_days(self):
        self.assertRowsEqual(self.run_query(self.con, "zero_days"), ref_zero_days(self.d), "zero_days")

    def test_summary(self):
        self.assertRowsEqual(self.run_query(self.con, "summary"), ref_summary(self.d),
                             "summary (the average divides by every day of the period, zero days included)")


class TestSecondDataset(SqlTestCase):
    def test_same_queries_on_new_data(self):
        d = {t: as_loaded(rows) for t, rows in make_data.build(seed=SECOND_SEED).items()}
        self.check_all(d, "second dataset (seed %d)" % SECOND_SEED)


def signup(uid, stamp):
    return {"user_id": uid, "signed_up_at_utc": stamp}


def period(start, end):
    return [{"start_date": start, "end_date": end}]


class TestEdgeCases(SqlTestCase):
    def test_no_signups(self):
        d = {"signups": [], "report_period": period("2026-09-01", "2026-09-07")}
        self.check_all(d, "no signups at all: every day of the period is a row with 0, and the average is 0.0")

    def test_ist_midnight(self):
        d = {
            "signups": [
                signup(1, "2026-08-31 18:29:59"),  # 31 Aug 23:59:59 IST, before the period
                signup(2, "2026-08-31 18:30:00"),  # 1 Sep 00:00:00 IST
                signup(3, "2026-09-01 18:29:59"),  # 1 Sep 23:59:59 IST
                signup(4, "2026-09-01 18:30:00"),  # 2 Sep 00:00:00 IST
                signup(5, "2026-09-02 23:00:00"),  # 3 Sep 04:30 IST, after the period
            ],
            "report_period": period("2026-09-01", "2026-09-02"),
        }
        self.check_all(d, "IST midnight is 18:30 UTC the day before: 18:30:00 UTC on 31 August is 1 September in "
                          "IST, and 18:29:59 is still 31 August")

    def test_zero_days_at_both_ends(self):
        d = {
            "signups": [signup(1, "2026-09-02 06:00:00"), signup(2, "2026-09-02 07:00:00")],
            "report_period": period("2026-09-01", "2026-09-04"),
        }
        self.check_all(d, "signups only on 2 September: 1, 3 and 4 September must still be rows with 0, so build "
                          "the days from report_period, not from the first and last signup")

    def test_month_and_year_end(self):
        d = {
            "signups": [signup(1, "2025-12-31 20:00:00"), signup(2, "2026-01-02 10:00:00")],
            "report_period": period("2025-12-30", "2026-01-02"),
        }
        self.check_all(d, "a period from 30 December 2025 to 2 January 2026 has 4 days, and 31 December 20:00 UTC "
                          "is 1 January in IST")

    def test_february(self):
        d = {"signups": [signup(1, "2026-02-28 12:00:00")], "report_period": period("2026-02-27", "2026-03-02")}
        self.check_all(d, "2026 is not a leap year: 27 February to 2 March is 4 days, with no 29 February")

    def test_single_day(self):
        d = {"signups": [signup(1, "2026-09-10 03:00:00")], "report_period": period("2026-09-10", "2026-09-10")}
        self.check_all(d, "a period of one day gives exactly one row")


if __name__ == "__main__":
    unittest.main()
