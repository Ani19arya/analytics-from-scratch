"""Tests for lesson 03: window functions.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

The expected answers are computed with plain Python loops over sorted rows,
never with a window function. Your queries run on three kinds of data:
1. the committed data/*.csv,
2. a second dataset built in memory with make_data.build(seed=2026), so a
   query that just types out the answers cannot pass,
3. tiny hand-made tables for the edge cases: empty tables, a three-way tie,
   a region with one rep, a month with no revenue figure (NULL) and a month
   with zero revenue.
"""
import csv
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

TABLES = {
    "monthly_revenue": ["region", "month", "revenue"],
    "rep_sales": ["rep", "region", "sales"],
}
QUERIES = ["running_total", "rep_rank", "top_reps", "month_over_month", "rep_cumulative"]
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


# The reference answers: loops over sorted rows.

def months_in_order(d):
    return sorted(d["monthly_revenue"], key=lambda r: (r["region"], r["month"]))


def ref_running_total(d):
    out, running, last_region = [], None, None
    for r in months_in_order(d):
        if r["region"] != last_region:
            running, last_region = None, r["region"]
        if r["revenue"] is not None:  # SUM skips NULLs
            running = (running or 0) + r["revenue"]
        out.append((r["region"], r["month"], r["revenue"], running))
    return out


def ref_month_over_month(d):
    out, prev, last_region = [], None, None
    for r in months_in_order(d):
        if r["region"] != last_region:
            prev, last_region = None, r["region"]
        change = None if prev is None or r["revenue"] is None else r["revenue"] - prev
        out.append((r["region"], r["month"], r["revenue"], prev, change))
        prev = r["revenue"]
    return out


def reps_in_order(d):
    """Per region: reps sorted by sales (highest first), then rep name."""
    for region in sorted({r["region"] for r in d["rep_sales"]}):
        yield region, sorted((r for r in d["rep_sales"] if r["region"] == region), key=lambda r: (-r["sales"], r["rep"]))


def ref_rep_rank(d):
    out = []
    for region, group in reps_in_order(d):
        for i, r in enumerate(group):
            rank = 1 + sum(1 for o in group if o["sales"] > r["sales"])
            out.append((region, r["rep"], r["sales"], rank, i + 1))
    return out


def ref_top_reps(d):
    return sorted((r[0], r[1]) for r in ref_rep_rank(d) if r[3] == 1)


def ref_rep_cumulative(d):
    out = []
    for region, group in reps_in_order(d):
        running = 0
        for r in group:
            running += r["sales"]
            out.append((region, r["rep"], r["sales"], running))
    return out


REFERENCE = {
    "running_total": ref_running_total,
    "rep_rank": ref_rep_rank,
    "top_reps": ref_top_reps,
    "month_over_month": ref_month_over_month,
    "rep_cumulative": ref_rep_cumulative,
}


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

    def assertRowsEqual(self, actual, expected, where, tol=0.011):
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

    def check(self, d, name, where):
        self.assertRowsEqual(self.run_query(make_db(d), name), REFERENCE[name](d), "%s, %s" % (where, name))

    def check_all(self, d, where):
        for name in QUERIES:
            self.check(d, name, where)


class TestCommittedData(SqlTestCase):
    def setUp(self):
        self.d = {t: read_csv(t) for t in TABLES}

    def test_running_total(self):
        self.check(self.d, "running_total", "committed data (a fiscal year: it must not restart in January)")

    def test_rep_rank(self):
        expected = ref_rep_rank(self.d)
        self.assertTrue(any(a[3] == b[3] for a, b in zip(expected, expected[1:]) if a[0] == b[0]), "data should contain a tie")
        self.check(self.d, "rep_rank", "committed data")

    def test_top_reps_keeps_ties(self):
        self.check(self.d, "top_reps", "committed data (R04 and R05 tie at the top of North: keep both)")

    def test_month_over_month(self):
        self.check(self.d, "month_over_month", "committed data")

    def test_rep_cumulative_ties(self):
        self.check(self.d, "rep_cumulative",
                   "committed data (R04 and R05 tie on 60000: with ORDER BY sales alone the default RANGE frame "
                   "gives both 120000; add rep as a tie breaker and a ROWS frame)")


class TestSecondDataset(SqlTestCase):
    def test_same_queries_on_new_data(self):
        d = {t: as_loaded(rows) for t, rows in make_data.build(seed=SECOND_SEED).items()}
        self.check_all(d, "second dataset (seed %d): the same queries on new numbers, so a typed-out answer fails here" % SECOND_SEED)


def month(region, m, revenue):
    return {"region": region, "month": m, "revenue": revenue}


def rep(name, region, sales):
    return {"rep": name, "region": region, "sales": sales}


class TestEdgeCases(SqlTestCase):
    def test_empty_tables(self):
        self.check_all({"monthly_revenue": [], "rep_sales": []}, "empty tables (every query should return no rows)")

    def test_three_way_tie_and_single_rep(self):
        d = {
            "monthly_revenue": [],
            "rep_sales": [rep("A", "East", 100), rep("C", "East", 100), rep("B", "East", 100), rep("D", "East", 90),
                          rep("E", "Hub", 70)],
        }
        self.check_all(d, "East has three reps tied on 100 (all rank 1, D is rank 4) and Hub has one rep")

    def test_null_and_zero_months(self):
        d = {
            "monthly_revenue": [month("East", "2026-01", 100), month("East", "2026-02", None),
                                month("East", "2026-03", 0), month("East", "2026-04", 50)],
            "rep_sales": [],
        }
        self.check_all(d, "East has no revenue figure for 2026-02 (NULL) and 0 for 2026-03: the running total "
                          "carries on (100, 100, 100, 150) and a change next to a NULL is NULL")


if __name__ == "__main__":
    unittest.main()
