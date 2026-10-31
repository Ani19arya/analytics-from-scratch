"""Tests for lesson 12: Tableau table calculations vs LOD.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

Every expected answer is computed here with plain Python dictionaries over the
raw sales lines, never read from the solution. The same checks run on the
committed CSV, on a second dataset built in memory with another seed, on a tiny
hand-made table (a tie, a region with no sales before April, a month with no
sales, a zero amount) and on an empty table.
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

SECOND_SEED = 4127
COLUMNS = ["line_id", "order_date", "region", "category", "amount"]
FILTER_REGION = "Coast"
Q2 = ("2026-04", "2026-06")


def cast(value):
    if value == "":
        return None
    for kind in (int, float):
        try:
            return kind(value)
        except ValueError:
            pass
    return value


def read_csv():
    with open(os.path.join(HERE, "data", "sales.csv"), newline="") as f:
        return [{k: cast(v) for k, v in row.items()} for row in csv.DictReader(f)]


def rows_from_build(seed):
    spec = importlib.util.spec_from_file_location("make_data", os.path.join(HERE, "make_data.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return [{k: cast(str(v)) for k, v in r.items()} for r in module.build(seed=seed)["sales"]]


def load_db(rows):
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE sales (%s)" % ", ".join(COLUMNS))
    con.executemany("INSERT INTO sales VALUES (?, ?, ?, ?, ?)", [[r[c] for c in COLUMNS] for r in rows])
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

def monthly(rows):
    out = {}
    for r in rows:
        key = (r["region"], r["order_date"][:7])
        out[key] = out.get(key, 0) + r["amount"]
    return out


def ref_running_total(rows):
    out, running = [], {}
    for (region, month), sales in sorted(monthly(rows).items()):
        running[region] = running.get(region, 0) + sales
        out.append((region, month, round(sales, 2), round(running[region], 2)))
    return out


def ref_rank(rows):
    sales = {}
    for r in rows:
        key = (r["region"], r["category"])
        sales[key] = sales.get(key, 0) + r["amount"]
    out = []
    for region in sorted({k[0] for k in sales}):
        values = [(c, round(v, 2)) for (g, c), v in sales.items() if g == region]
        for category, v in values:
            rank = 1 + sum(1 for _, other in values if other > v)
            out.append((region, category, v, rank))
    return sorted(out, key=lambda t: (t[0], t[3], t[1]))


def ratio(a, b):
    return None if b == 0 else round(a / b, 4)


def ref_share(rows):
    total_all = sum(r["amount"] for r in rows)
    sales = {}
    for r in rows:
        if r["region"] == FILTER_REGION:
            sales[r["category"]] = sales.get(r["category"], 0) + r["amount"]
    total_view = sum(sales.values())
    return [(c, round(v, 2), ratio(v, total_view), ratio(v, total_all)) for c, v in sorted(sales.items())]


def ref_q2(rows):
    out, running_all, running_q2 = [], {}, {}
    for (region, month), sales in sorted(monthly(rows).items()):
        running_all[region] = running_all.get(region, 0) + sales
        if Q2[0] <= month <= Q2[1]:
            running_q2[region] = running_q2.get(region, 0) + sales
            out.append((region, month, round(sales, 2), round(running_q2[region], 2), round(running_all[region], 2)))
    return out


# ---- The checks ---------------------------------------------------------------

class TableCalcChecks:
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

    def test_running_total_by_month(self):
        self.assertRowsEqual(self.run_query("running_total_by_month"), ref_running_total(self.rows),
                             "running_total_by_month (sum per region and month first, then a running sum that "
                             "restarts for each region)")

    def test_category_rank_by_region(self):
        self.assertRowsEqual(self.run_query("category_rank_by_region"), ref_rank(self.rows),
                             "category_rank_by_region (rank within each region, highest sales = 1, ties share a "
                             "rank and the next is skipped)")

    def test_share_with_region_filter(self):
        actual = self.run_query("share_with_region_filter")
        expected = ref_share(self.rows)
        for a, e in zip(actual, expected):
            if len(a) == 4 and e[3] is not None and a[3] is not None and abs(a[3] - e[2]) < 1e-4 \
                    and abs(e[2] - e[3]) > 1e-3:
                self.fail("share_with_region_filter: pct_of_all_regions for %s equals the share of Coast. "
                          "FIXED runs before the dimension filter: divide by every region's sales" % e[0])
        self.assertRowsEqual(actual, expected, "share_with_region_filter", tol=0.0002)

    def test_running_total_q2(self):
        actual = self.run_query("running_total_q2")
        expected = ref_q2(self.rows)
        self.assertRowsEqual(actual, expected,
                             "running_total_q2 (running_dimension_filter restarts in April; running_table_calc_filter "
                             "carries January to March)")


class TestCommittedData(TableCalcChecks, unittest.TestCase):
    rows = read_csv()

    def test_data_has_sales_before_april(self):
        self.assertTrue(any(r["order_date"] < "2026-04" for r in self.rows), "data should start before April")


class TestSecondDataset(TableCalcChecks, unittest.TestCase):
    """Built in memory with another seed: hard-coded answers fail here."""
    rows = rows_from_build(SECOND_SEED)


class TestTinyEdgeCases(TableCalcChecks, unittest.TestCase):
    """Coast: Boots and Packs tie on 50.00, Tents is 0.00, no sales in February.
    Lakes has no sales before April. Alpine has only March sales."""
    rows = [
        {"line_id": 1, "order_date": "2026-01-10", "region": "Coast", "category": "Boots", "amount": 50.0},
        {"line_id": 2, "order_date": "2026-03-05", "region": "Coast", "category": "Packs", "amount": 20.0},
        {"line_id": 3, "order_date": "2026-04-02", "region": "Coast", "category": "Packs", "amount": 30.0},
        {"line_id": 4, "order_date": "2026-05-20", "region": "Coast", "category": "Tents", "amount": 0.0},
        {"line_id": 5, "order_date": "2026-04-15", "region": "Lakes", "category": "Boots", "amount": 80.0},
        {"line_id": 6, "order_date": "2026-06-30", "region": "Lakes", "category": "Clothing", "amount": 15.5},
        {"line_id": 7, "order_date": "2026-03-31", "region": "Alpine", "category": "Tents", "amount": 200.0},
    ]

    def test_reference_has_the_tie(self):
        coast = [r for r in ref_rank(self.rows) if r[0] == "Coast"]
        self.assertEqual([r[3] for r in coast], [1, 1, 3], "the tiny case should have a tie then a skipped rank")


class TestEmptyTable(TableCalcChecks, unittest.TestCase):
    """No sales at all: every query returns no rows instead of an error."""
    rows = []


if __name__ == "__main__":
    unittest.main()
