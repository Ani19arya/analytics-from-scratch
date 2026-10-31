"""Tests for lesson 02: DAX measures from scratch.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

Every expected answer is computed here with plain Python loops over the raw
rows, never read from the solution. The same checks run on three datasets:
the committed CSV, a second dataset built in memory with another seed, and a
tiny hand-made table (a zero amount, a tie, a year with no online sales).
"""
import csv
import importlib.util
import os
import re
import sqlite3
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if os.environ.get("CHECK_SOLUTION") == "1":
    SQL_FILE = os.path.join(HERE, "solution", "solution.sql")
else:
    SQL_FILE = os.path.join(HERE, "exercise.sql")

SECOND_SEED = 4027
SLICER_YEAR = "2026"


def cast(value):
    if value == "":
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


def rows_from_build(seed):
    spec = importlib.util.spec_from_file_location("make_data", os.path.join(HERE, "make_data.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return [{k: cast(str(v)) for k, v in r.items()} for r in module.build(seed=seed)["sales"]]


def load_db(rows):
    con = sqlite3.connect(":memory:")
    cols = ["order_date", "category", "channel", "amount"]
    con.execute("CREATE TABLE sales (%s)" % ", ".join(cols))
    con.executemany("INSERT INTO sales VALUES (?, ?, ?, ?)", [[r[c] for c in cols] for r in rows])
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


# ---- Plain Python references ------------------------------------------------

def total(rows):
    return sum(r["amount"] for r in rows)


def ref_sales_by_category(rows):
    grand = total(rows)
    out = []
    for cat in sorted({r["category"] for r in rows}):
        mine = [r for r in rows if r["category"] == cat]
        online = [r for r in mine if r["channel"] == "Online"]
        out.append((cat, round(total(mine), 2), round(total(online), 2), round(total(mine) / grand, 4)))
    return out


def ref_share_with_year_slicer(rows):
    sliced = [r for r in rows if r["order_date"][:4] == SLICER_YEAR]
    grand = total(sliced)
    return [(cat, round(total([r for r in sliced if r["category"] == cat]), 2),
             round(total([r for r in sliced if r["category"] == cat]) / grand, 4))
            for cat in sorted({r["category"] for r in sliced})]


def ref_channel_matrix(rows):
    sliced = [r for r in rows if r["order_date"][:4] == SLICER_YEAR]
    online = [r for r in sliced if r["channel"] == "Online"]
    online_total = round(total(online), 2) if online else None  # DAX: blank, not 0
    out = []
    for ch in sorted({r["channel"] for r in sliced}):
        mine = [r for r in sliced if r["channel"] == ch]
        keep = [r for r in mine if r["channel"] == "Online"]
        out.append((ch, round(total(mine), 2), online_total, round(total(keep), 2) if keep else None))
    return out


def monthly(rows):
    out = {}
    for r in rows:
        out[r["order_date"][:7]] = out.get(r["order_date"][:7], 0) + r["amount"]
    return out


def ref_sales_ytd(rows):
    by_month = monthly(rows)
    first, last = min(by_month), max(by_month)
    y, m = int(first[:4]), int(first[5:])
    out, running, year = [], 0, None
    while "%04d-%02d" % (y, m) <= last:
        ym = "%04d-%02d" % (y, m)
        if y != year:
            running, year = 0, y
        sales = by_month.get(ym, 0)
        running += sales
        out.append((ym, round(float(sales), 2), round(float(running), 2)))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def ref_sales_vs_last_year(rows):
    by_month = monthly(rows)
    out = []
    for ym in sorted(k for k in by_month if k >= "2026-01"):
        ly = by_month.get("%04d%s" % (int(ym[:4]) - 1, ym[4:]), 0)
        growth = None if ly == 0 else round((by_month[ym] - ly) * 100.0 / ly, 1)
        out.append((ym, round(by_month[ym], 2), round(float(ly), 2), growth))
    return out


# ---- The checks ---------------------------------------------------------------

class MeasureChecks:
    rows = None

    @classmethod
    def setUpClass(cls):
        cls.con = load_db(cls.rows)
        cls.queries = load_queries(SQL_FILE)

    def run_query(self, name):
        sql = self.queries.get(name, "")
        if not sql:
            self.fail("query '%s' is empty in %s: write it first" % (name, os.path.basename(SQL_FILE)))
        return [tuple(r) for r in self.con.execute(sql).fetchall()]

    def assertRowsEqual(self, actual, expected, what, tol=0.011):
        self.assertEqual(len(actual), len(expected),
                         "%s: got %d rows, expected %d" % (what, len(actual), len(expected)))
        for a, e in zip(actual, expected):
            self.assertEqual(len(a), len(e), "%s: row %r should have the columns of %r" % (what, a, e))
            for x, y in zip(a, e):
                if isinstance(y, float):
                    self.assertIsNotNone(x, "%s: got NULL in %r, expected %r" % (what, a, e))
                    self.assertAlmostEqual(x, y, delta=tol, msg="%s: row %r, expected %r" % (what, a, e))
                else:
                    self.assertEqual(x, y, "%s: row %r, expected %r" % (what, a, e))

    def test_sales_by_category(self):
        self.assertRowsEqual(self.run_query("sales_by_category"), ref_sales_by_category(self.rows),
                             "sales_by_category", tol=0.0002)

    def test_share_keeps_the_year_slicer(self):
        actual = self.run_query("share_with_year_slicer")
        expected = ref_share_with_year_slicer(self.rows)
        if actual and len(actual[0]) == 3 and all(r[2] is not None for r in actual):
            got = sum(r[2] for r in actual)
            self.assertAlmostEqual(got, 1.0, delta=0.001,
                                   msg="shares add up to %.4f, not 1: ALL(category) removes the category filter "
                                       "only, so the denominator must keep the year slicer" % got)
        self.assertRowsEqual(actual, expected, "share_with_year_slicer", tol=0.0002)

    def test_channel_matrix_calculate_replaces_keepfilters_intersects(self):
        actual = self.run_query("channel_matrix")
        expected = ref_channel_matrix(self.rows)
        for a, e in zip(actual, expected):
            if len(a) == 4 and e[0] != "Online" and e[2] is not None and a[2] in (0, None):
                self.fail("row %r: CALCULATE with channel = Online REPLACES the row's channel filter, "
                          "so the %s row shows the online total %.2f, not 0 or NULL" % (a, e[0], e[2]))
            if len(a) == 4 and e[0] != "Online" and a[3] == 0:
                self.fail("row %r: KEEPFILTERS leaves no rows on the %s row, which is blank (NULL), not 0" % (a, e[0]))
        self.assertRowsEqual(actual, expected, "channel_matrix")

    def test_sales_ytd_has_every_month_and_restarts_in_january(self):
        self.assertRowsEqual(self.run_query("sales_ytd"), ref_sales_ytd(self.rows), "sales_ytd")

    def test_sales_vs_last_year_matches_calendar_month(self):
        actual = self.run_query("sales_vs_last_year")
        expected = ref_sales_vs_last_year(self.rows)
        self.assertRowsEqual(actual, expected, "sales_vs_last_year (shift the calendar by one year, do not count back rows)",
                             tol=0.051)
        for a, e in zip(actual, expected):
            if e[3] is None:
                self.assertIsNone(a[3], "growth must be NULL when last year had no sales: row %r" % (a,))


class TestCommittedData(MeasureChecks, unittest.TestCase):
    rows = read_csv("sales")

    def test_data_has_the_traps(self):
        self.assertIn(0.0, [e[1] for e in ref_sales_ytd(self.rows)], "data should contain a month with no sales")
        self.assertIn(None, [e[3] for e in ref_sales_vs_last_year(self.rows)],
                      "data should contain a month with no sales last year")


class TestSecondDataset(MeasureChecks, unittest.TestCase):
    """Built in memory with another seed: hard-coded answers fail here."""
    rows = rows_from_build(SECOND_SEED)


class TestTinyEdgeCases(MeasureChecks, unittest.TestCase):
    """A zero amount, Beans and Subscriptions tied in 2026, no online sales in 2026
    (so CALCULATE gives blank on every row), a growth of -50% and two with no base."""
    rows = [
        {"order_date": "2025-01-10", "category": "Beans", "channel": "Online", "amount": 10.0},
        {"order_date": "2025-01-20", "category": "Equipment", "channel": "Retail", "amount": 30.0},
        {"order_date": "2026-01-05", "category": "Beans", "channel": "Retail", "amount": 20.0},
        {"order_date": "2026-01-06", "category": "Beans", "channel": "Retail", "amount": 0.0},
        {"order_date": "2026-02-01", "category": "Equipment", "channel": "Retail", "amount": 40.0},
        {"order_date": "2026-03-01", "category": "Subscriptions", "channel": "Retail", "amount": 20.0},
    ]


if __name__ == "__main__":
    unittest.main()
