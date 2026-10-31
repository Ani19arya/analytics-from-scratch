"""Tests for lesson 14: SQL dialects for work and interviews.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

The expected answers are computed with plain Python (datetime, loops), never
with SQL. Every query runs twice on each dataset: once as SQLite runs it by
default, and once with PRAGMA case_sensitive_like = ON, which makes LIKE
case-sensitive as it is in Postgres, BigQuery and Snowflake. A portable query
gives the same answer both times.
Datasets: the committed data/*.csv, a second dataset built in memory with
make_data.build(seed=2028), and tiny hand-made tables for the edge cases: no
orders, a Sunday and the Monday after it, a promo code in three spellings, a
NULL promo code, two orders in the same second, a customer with one order, a
second order just after midnight, and an average that is not a whole number.
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

TABLES = {"customers": ["customer_id", "city", "signed_up_on"],
          "orders": ["order_id", "customer_id", "ordered_at", "amount", "status", "promo_code"]}
SECOND_SEED = 2028
QUERIES = ["monthly_revenue", "weekly_orders", "city_aov", "latest_order", "second_order_gap"]
HINT = {
    "monthly_revenue": "the first day of each month as 'YYYY-MM-01', with completed orders and their revenue",
    "weekly_orders": "weeks start on Monday here; check where your query puts a Sunday order",
    "city_aov": "divide as decimals, and match 'fest' at the start in any mix of capitals even when LIKE is "
                "case-sensitive (LOYALFEST does not start with fest)",
    "latest_order": "the latest completed order per customer; on a tie in time, the larger order_id",
    "second_order_gap": "days between the two order dates, NULL with no second order, and NULLs sorted last "
                        "(SQLite sorts them first unless you say otherwise)",
}


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
    return [{k: cast(None if v is None else str(v)) for k, v in r.items()} for r in rows]


def make_db(data, strict):
    con = sqlite3.connect(":memory:")
    if strict:
        con.execute("PRAGMA case_sensitive_like = ON")
    for table, cols in TABLES.items():
        con.execute("CREATE TABLE %s (%s)" % (table, ", ".join(cols)))
        con.executemany("INSERT INTO %s VALUES (%s)" % (table, ", ".join("?" * len(cols))),
                        [[r.get(c) for c in cols] for r in data.get(table, [])])
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


def round_half_up(x, places):
    """Round the way SQLite's ROUND does: halves away from zero."""
    f = 10 ** places
    return math.floor(x * f + 0.5) / f


# The reference answers, in plain Python.

def day_of(o):
    return datetime.date(*map(int, o["ordered_at"][:10].split("-")))


def completed(d):
    return [o for o in d["orders"] if o["status"] == "completed"]


def ref(d, name):
    done = completed(d)
    if name == "monthly_revenue":
        per = {}
        for o in done:
            s = per.setdefault(o["ordered_at"][:7] + "-01", [0, 0])
            s[0] += 1
            s[1] += o["amount"]
        return [(k, n, r) for k, (n, r) in sorted(per.items())]
    if name == "weekly_orders":
        per = {}
        for o in done:
            day = day_of(o)
            monday = (day - datetime.timedelta(days=day.weekday())).isoformat()
            per[monday] = per.get(monday, 0) + 1
        return sorted(per.items())
    if name == "city_aov":
        city = {c["customer_id"]: c["city"] for c in d["customers"]}
        per = {}
        for o in done:
            if o["customer_id"] not in city:
                continue
            s = per.setdefault(city[o["customer_id"]], [0, 0, 0])
            s[0] += 1
            s[1] += o["amount"]
            code = o["promo_code"]
            s[2] += 1 if code is not None and str(code).lower().startswith("fest") else 0
        return [(c, n, r, round_half_up(r / n, 2), round_half_up(f / n, 4)) for c, (n, r, f) in sorted(per.items())]
    by_cust = {}
    for o in done:
        by_cust.setdefault(o["customer_id"], []).append(o)
    if name == "latest_order":
        out = []
        for c in sorted(by_cust):
            o = max(by_cust[c], key=lambda x: (x["ordered_at"], x["order_id"]))
            out.append((c, o["order_id"], o["ordered_at"], o["amount"]))
        return out
    out = []
    for c, rows in by_cust.items():
        rows = sorted(rows, key=lambda x: (x["ordered_at"], x["order_id"]))
        gap = (day_of(rows[1]) - day_of(rows[0])).days if len(rows) > 1 else None
        out.append((c, day_of(rows[0]).isoformat(), gap))
    return sorted(out, key=lambda r: (r[2] is None, r[2] if r[2] is not None else 0, r[0]))


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

    def check(self, d, name, where):
        expected = ref(d, name)
        for strict in (False, True):
            con = make_db(d, strict)
            got = self.run_query(con, name)
            con.close()
            mode = "with case-sensitive LIKE" if strict else "with SQLite's defaults"
            self.assertEqual(len(got), len(expected), "%s, %s (%s): got %d rows, expected %d; %s"
                             % (where, name, mode, len(got), len(expected), HINT[name]))
            for g, e in zip(got, expected):
                same = len(g) == len(e) and all(
                    (x is None and y is None) or (x is not None and y is not None and
                                                  (abs(x - y) < 1e-6 if isinstance(y, float) else x == y))
                    for x, y in zip(g, e))
                self.assertTrue(same, "%s, %s (%s): row %r, expected %r; %s"
                                % (where, name, mode, g, e, HINT[name]))


class TestCommittedData(SqlTestCase):
    def setUp(self):
        self.d = {t: read_csv(t) for t in TABLES}

    def test_monthly_revenue(self):
        self.check(self.d, "monthly_revenue", "committed data")

    def test_weekly_orders(self):
        self.check(self.d, "weekly_orders", "committed data")

    def test_city_aov(self):
        self.check(self.d, "city_aov", "committed data")

    def test_latest_order(self):
        self.check(self.d, "latest_order", "committed data")

    def test_second_order_gap(self):
        self.check(self.d, "second_order_gap", "committed data")


class TestSecondDataset(SqlTestCase):
    def test_all_queries(self):
        d = {t: as_loaded(rows) for t, rows in make_data.build(seed=SECOND_SEED).items()}
        for name in QUERIES:
            self.check(d, name, "second dataset (seed %d)" % SECOND_SEED)


def tables(orders, customers=None):
    """orders: (order_id, customer_id, ordered_at, amount[, promo_code[, status]])."""
    customers = customers or [{"customer_id": "A", "city": "Pune", "signed_up_on": "2026-08-01"},
                              {"customer_id": "B", "city": "Nagpur", "signed_up_on": "2026-08-01"}]
    rows = [{"order_id": o[0], "customer_id": o[1], "ordered_at": o[2], "amount": o[3],
             "promo_code": o[4] if len(o) > 4 else None, "status": o[5] if len(o) > 5 else "completed"}
            for o in orders]
    return {"customers": customers, "orders": rows}


class TestEdgeCases(SqlTestCase):
    def test_empty(self):
        for name in QUERIES:
            self.check(tables([]), name, "no orders (every query returns no rows)")

    def test_sunday_and_monday(self):
        d = tables([(1, "A", "2026-10-25 21:00:00", 100), (2, "A", "2026-10-26 08:00:00", 100),
                    (3, "B", "2026-11-01 23:59:59", 100), (4, "B", "2026-10-31 10:00:00", 100, None, "cancelled")])
        self.check(d, "weekly_orders", "Sunday 25 October is in the week of Monday 19 October; Monday 26 October "
                                       "and Sunday 1 November are in the week of 26 October")
        self.check(d, "monthly_revenue", "1 November 23:59:59 is in November")

    def test_promo_spellings(self):
        d = tables([(1, "A", "2026-10-01 10:00:00", 100, "FEST10"), (2, "A", "2026-10-02 10:00:00", 101, "fest10"),
                    (3, "A", "2026-10-03 10:00:00", 102, "Fest25"), (4, "A", "2026-10-04 10:00:00", 103, None),
                    (5, "A", "2026-10-05 10:00:00", 104, "LOYALFEST"), (6, "B", "2026-10-05 11:00:00", 50)])
        self.check(d, "city_aov", "three spellings of a fest code count, NULL and LOYALFEST do not: Pune is "
                                  "5 orders, 510 revenue, 102.0 average, 0.6 fest share")

    def test_not_a_whole_number(self):
        d = tables([(1, "A", "2026-10-01 10:00:00", 100), (2, "A", "2026-10-02 10:00:00", 101),
                    (3, "A", "2026-10-03 10:00:00", 101)])
        self.check(d, "city_aov", "302 over 3 orders is 100.67, not 100")

    def test_same_second(self):
        d = tables([(7, "A", "2026-10-05 20:00:00", 100), (9, "A", "2026-10-05 20:00:00", 200),
                    (3, "A", "2026-09-01 20:00:00", 300)])
        self.check(d, "latest_order", "orders 7 and 9 are at the same second: the latest is 9")
        self.check(d, "second_order_gap", "first is order 3 on 1 September, second is order 7 on 5 October")

    def test_gaps_and_nulls(self):
        d = tables([(1, "A", "2026-10-05 23:59:00", 100), (2, "A", "2026-10-06 00:01:00", 100),
                    (3, "B", "2026-10-01 12:00:00", 100), (4, "B", "2026-10-09 12:00:00", 100, None, "cancelled")],
                   customers=[{"customer_id": "A", "city": "Pune", "signed_up_on": "2026-08-01"},
                              {"customer_id": "B", "city": "Pune", "signed_up_on": "2026-08-01"}])
        self.check(d, "second_order_gap", "A's second order is 2 minutes later but on the next date (1 day); B has "
                                          "only one completed order, so NULL, sorted last")


if __name__ == "__main__":
    unittest.main()
