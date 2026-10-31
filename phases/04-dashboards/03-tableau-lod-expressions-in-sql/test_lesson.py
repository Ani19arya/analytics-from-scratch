"""Tests for lesson 03: Tableau LOD expressions in SQL.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

Every expected answer is computed here with plain Python dictionaries over the
raw orders, never read from the solution. The same checks run on the committed
CSV, on a second dataset built in memory with another seed, on a tiny
hand-made table (a tie, one-order customers, a region with one customer) and
on an empty table.
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

SECOND_SEED = 4031
COLUMNS = ["order_id", "customer_id", "region", "order_date", "amount"]


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
    return [{k: cast(str(v)) for k, v in r.items()} for r in module.build(seed=seed)["orders"]]


def load_db(rows):
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE orders (%s)" % ", ".join(COLUMNS))
    con.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", [[r[c] for c in COLUMNS] for r in rows])
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

def per_customer(orders):
    first, sales, region_of = {}, {}, {}
    for r in orders:
        c, m = r["customer_id"], r["order_date"][:7]
        first[c] = min(first.get(c, m), m)
        sales[c] = sales.get(c, 0) + r["amount"]
        region_of[c] = r["region"]
    return first, sales, region_of


def ref_customer_first_month(orders):
    first, _, _ = per_customer(orders)
    return sorted(first.items())


def ref_new_customers_by_month(orders):
    first, _, _ = per_customer(orders)
    counts = {}
    for m in first.values():
        counts[m] = counts.get(m, 0) + 1
    return sorted(counts.items())


def ref_avg_customer_sales_by_region(orders):
    _, sales, region_of = per_customer(orders)
    out = []
    for region in sorted(set(region_of.values())):
        vals = [v for c, v in sales.items() if region_of[c] == region]
        out.append((region, len(vals), round(sum(vals) / len(vals), 2)))
    return out


def ref_region_month_share(orders):
    monthly, region_total = {}, {}
    for r in orders:
        key = (r["region"], r["order_date"][:7])
        monthly[key] = monthly.get(key, 0) + r["amount"]
        region_total[r["region"]] = region_total.get(r["region"], 0) + r["amount"]
    return [(k[0], k[1], round(v, 2), round(region_total[k[0]], 2), round(v / region_total[k[0]], 4))
            for k, v in sorted(monthly.items())]


def ref_customer_share_of_region(orders):
    _, sales, region_of = per_customer(orders)
    region_total = {}
    for c, v in sales.items():
        region_total[region_of[c]] = region_total.get(region_of[c], 0) + v
    ordered = sorted(sales.items(), key=lambda kv: (region_of[kv[0]], -round(kv[1], 2), kv[0]))
    return [(c, region_of[c], round(v, 2), round(region_total[region_of[c]], 2),
             round(v / region_total[region_of[c]], 4)) for c, v in ordered]


# ---- The checks ---------------------------------------------------------------

class LodChecks:
    orders = None

    @classmethod
    def setUpClass(cls):
        cls.con = load_db(cls.orders)
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

    def test_customer_first_month(self):
        self.assertRowsEqual(self.run_query("customer_first_month"), ref_customer_first_month(self.orders),
                             "customer_first_month")

    def test_new_customers_by_month(self):
        self.assertRowsEqual(self.run_query("new_customers_by_month"), ref_new_customers_by_month(self.orders),
                             "new_customers_by_month (count each customer once, in the month of their FIRST order)")

    def test_avg_customer_sales_by_region(self):
        self.assertRowsEqual(self.run_query("avg_customer_sales_by_region"),
                             ref_avg_customer_sales_by_region(self.orders),
                             "avg_customer_sales_by_region (sum per customer first, then average)")

    def test_region_month_share(self):
        self.assertRowsEqual(self.run_query("region_month_share"), ref_region_month_share(self.orders),
                             "region_month_share", tol=0.0002)

    def test_customer_share_of_region(self):
        self.assertRowsEqual(self.run_query("customer_share_of_region"), ref_customer_share_of_region(self.orders),
                             "customer_share_of_region (order by region, customer_sales DESC, customer_id)",
                             tol=0.0002)


class TestCommittedData(LodChecks, unittest.TestCase):
    orders = read_csv("orders")

    def test_data_has_repeat_customers(self):
        active = {}
        for r in self.orders:
            active.setdefault(r["order_date"][:7], set()).add(r["customer_id"])
        new = ref_new_customers_by_month(self.orders)
        self.assertNotEqual([len(active[m]) for m, _ in new], [n for _, n in new], "data should have repeat customers")


class TestSecondDataset(LodChecks, unittest.TestCase):
    """Built in memory with another seed: hard-coded answers fail here."""
    orders = rows_from_build(SECOND_SEED)


class TestTinyEdgeCases(LodChecks, unittest.TestCase):
    """C2 and C3 tie on 50.00 (the tie breaks on customer_id), C1 orders in two
    months, C3 has a single order, and Lakes has one customer who is 100% of it."""
    orders = [
        {"order_id": "O1", "customer_id": "C1", "region": "Alpine", "order_date": "2025-01-05", "amount": 10.0},
        {"order_id": "O2", "customer_id": "C2", "region": "Alpine", "order_date": "2025-01-20", "amount": 50.0},
        {"order_id": "O3", "customer_id": "C1", "region": "Alpine", "order_date": "2025-02-02", "amount": 30.0},
        {"order_id": "O4", "customer_id": "C3", "region": "Alpine", "order_date": "2025-02-10", "amount": 50.0},
        {"order_id": "O5", "customer_id": "C4", "region": "Lakes", "order_date": "2025-02-11", "amount": 0.0},
        {"order_id": "O6", "customer_id": "C4", "region": "Lakes", "order_date": "2025-03-01", "amount": 25.0},
    ]


class TestEmptyTable(LodChecks, unittest.TestCase):
    """No orders at all: every query returns no rows instead of an error or a row of NULLs."""
    orders = []


if __name__ == "__main__":
    unittest.main()
