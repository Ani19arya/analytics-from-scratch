"""Tests for lesson 09: rolling averages and percent of total.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

The expected answers are computed with plain Python lists and dates, never
with SQL. Your queries run on three kinds of data:
1. the committed data/*.csv,
2. a second dataset built in memory with make_data.build(seed=2026), so a
   query that just types out the answers cannot pass,
3. tiny hand-made tables for the edge cases: no orders at all (zeros), a
   period shorter than a week (NULL averages), a missing day inside the
   window, two regions with the same revenue (a tie), an order with no region
   (NULL), an order outside the period, and a period with zero revenue.
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

TABLES = {"orders": ["order_id", "order_date", "region", "amount"], "report_period": ["start_date", "end_date"]}
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


def round_to(x, places):
    """Round halves away from zero, the way SQLite's ROUND does."""
    f = 10 ** places
    return math.floor(x * f + 0.5) / f


# The reference answers, in plain Python.

def period_days(d):
    if not d["report_period"]:
        return []
    p = d["report_period"][0]
    day = datetime.date.fromisoformat(p["start_date"])
    end = datetime.date.fromisoformat(p["end_date"])
    out = []
    while day <= end:
        out.append(day.isoformat())
        day += datetime.timedelta(days=1)
    return out


def ref_daily_orders(d):
    counts, revenue = {}, {}
    for o in d["orders"]:
        counts[o["order_date"]] = counts.get(o["order_date"], 0) + 1
        revenue[o["order_date"]] = revenue.get(o["order_date"], 0) + o["amount"]
    return [(day, counts.get(day, 0), revenue.get(day, 0)) for day in period_days(d)]


def ref_moving_avg(d):
    daily = ref_daily_orders(d)
    out = []
    for i, (day, n, _) in enumerate(daily):
        if i < 6:
            out.append((day, n, None))           # fewer than 7 calendar days of history
        else:
            out.append((day, n, round_to(sum(r[1] for r in daily[i - 6:i + 1]) / 7, 2)))
    return out


def ref_region_share(d):
    days = set(period_days(d))
    revenue = {}
    for o in d["orders"]:
        if o["order_date"] in days:
            region = o["region"] if o["region"] is not None else "Unassigned"
            revenue[region] = revenue.get(region, 0) + o["amount"]
    total = sum(revenue.values())
    rows = [(r, v, round_to(100.0 * v / total, 1) if total else None) for r, v in revenue.items()]
    return sorted(rows, key=lambda t: (-t[1], t[0]))


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
        self.assertRowsEqual(self.run_query(con, "daily_orders"), ref_daily_orders(d), where + ", daily_orders")
        self.assertRowsEqual(self.run_query(con, "moving_avg"), ref_moving_avg(d), where + ", moving_avg")
        self.assertRowsEqual(self.run_query(con, "region_share"), ref_region_share(d), where + ", region_share",
                             tol=0.051)


class TestCommittedData(SqlTestCase):
    def setUp(self):
        self.d = {t: read_csv(t) for t in TABLES}
        self.con = make_db(self.d)

    def test_daily_orders(self):
        got = self.run_query(self.con, "daily_orders")
        self.assertEqual(len(got), len(period_days(self.d)),
                         "daily_orders should have one row for every day of the report period, including the "
                         "Sundays and shut days with no orders; build a date spine")
        self.assertRowsEqual(got, ref_daily_orders(self.d), "daily_orders")

    def test_moving_avg(self):
        self.assertRowsEqual(self.run_query(self.con, "moving_avg"), ref_moving_avg(self.d),
                             "moving_avg (average over the last 7 calendar days, zero days included)")

    def test_region_share(self):
        got = self.run_query(self.con, "region_share")
        self.assertRowsEqual(got, ref_region_share(self.d), "region_share", tol=0.051)


class TestSecondDataset(SqlTestCase):
    def test_same_queries_on_new_data(self):
        d = {t: as_loaded(rows) for t, rows in make_data.build(seed=SECOND_SEED).items()}
        self.check_all(d, "second dataset (seed %d)" % SECOND_SEED)


def period(start, end):
    return [{"start_date": start, "end_date": end}]


def orders(spec):
    """spec: list of (date, region, amount) -> order rows."""
    return [{"order_id": n, "order_date": day, "region": region, "amount": amount}
            for n, (day, region, amount) in enumerate(spec, 1)]


class TestEdgeCases(SqlTestCase):
    def test_no_orders(self):
        self.check_all({"orders": [], "report_period": period("2026-09-01", "2026-09-08")},
                       "no orders at all: every day shows 0 orders, the average from day 7 on is 0.0, and "
                       "region_share has no rows")

    def test_short_period(self):
        d = {"orders": orders([("2026-09-01", "North", 100), ("2026-09-03", "South", 300)]),
             "report_period": period("2026-09-01", "2026-09-05")}
        self.check_all(d, "a 5-day period never has 7 days of history, so every avg_7d is NULL")

    def test_missing_day_in_window(self):
        spec = [("2026-09-%02d" % day, "North", 100) for day in (1, 2, 3, 5, 6, 7, 8)]
        spec += [("2026-09-08", "West", 100)]
        d = {"orders": orders(spec), "report_period": period("2026-09-01", "2026-09-08")}
        self.check_all(d, "4 September has no orders: on 7 September the last 7 days hold 6 orders, so the "
                          "average is 6/7 = 0.86, not 1.0, and on 8 September it is 7/7 = 1.0")

    def test_tie_null_region_and_outside_period(self):
        d = {"orders": orders([("2026-09-01", "North", 500), ("2026-09-02", "South", 500),
                               ("2026-09-02", None, 250), ("2026-08-31", "West", 9999)]),
             "report_period": period("2026-09-01", "2026-09-02")}
        self.check_all(d, "North and South tie at 500 (order the tie by region), the order with no region is "
                          "Unassigned, and the 31 August order is outside the period")

    def test_zero_revenue(self):
        d = {"orders": orders([("2026-09-01", "North", 0), ("2026-09-01", "South", 0)]),
             "report_period": period("2026-09-01", "2026-09-01")}
        self.check_all(d, "total revenue is 0, so a share is undefined: return NULL, not an error and not 0")


if __name__ == "__main__":
    unittest.main()
