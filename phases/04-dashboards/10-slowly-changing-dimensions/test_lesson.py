"""Tests for lesson 10: slowly changing dimensions.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

Every expected answer is computed here in plain Python over the raw change log
and orders, never read from the solution. The Type 2 dimension that the last
three queries join to (dim_customer) is loaded from the test's own reference,
so each query is checked on its own. The same checks run on the committed CSV
files, on a second dataset built in memory with another seed, on a hand-made
log (a same-day correction, a repeated region, a move entered late, an order on
the day of a move, an order before the first record, a customer with no record,
a zero amount) and on empty tables.
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

SECOND_SEED = 4107
OPEN_END = "9999-12-31"
TABLES = {
    "customer_changes": ["change_id", "customer_id", "region", "changed_on"],
    "orders": ["order_id", "customer_id", "order_date", "amount"],
}
DIM_COLUMNS = ["customer_key", "customer_id", "region", "valid_from", "valid_to", "is_current"]


def cast(value):
    if value == "" or value is None:
        return None
    if not isinstance(value, str):
        return value
    for kind in (int, float):
        try:
            return kind(value)
        except ValueError:
            pass
    return value


def read_csv_tables():
    out = {}
    for table in TABLES:
        with open(os.path.join(HERE, "data", table + ".csv"), newline="") as f:
            out[table] = [{k: cast(v) for k, v in row.items()} for row in csv.DictReader(f)]
    return out


def tables_from_build(seed):
    spec = importlib.util.spec_from_file_location("make_data", os.path.join(HERE, "make_data.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    built = module.build(seed=seed)
    return {t: [{k: cast(str(v)) for k, v in r.items()} for r in rows] for t, rows in built.items()}


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

def saves_by_customer(changes):
    """One save per customer and day (the highest change_id wins), in date order."""
    best = {}
    for c in changes:
        key = (c["customer_id"], c["changed_on"])
        if key not in best or c["change_id"] > best[key]["change_id"]:
            best[key] = c
    out = {}
    for (cid, day) in sorted(best):
        out.setdefault(cid, []).append(best[(cid, day)])
    return out


def ref_type1(tables):
    return [(cid, saves[-1]["region"]) for cid, saves in sorted(saves_by_customer(tables["customer_changes"]).items())]


def ref_type2(tables):
    rows = []
    for cid, saves in sorted(saves_by_customer(tables["customer_changes"]).items()):
        versions = []
        for s in saves:
            if not versions or versions[-1][1] != s["region"]:
                versions.append((cid, s["region"], s["changed_on"]))
        for i, (c, region, start) in enumerate(versions):
            last = i == len(versions) - 1
            rows.append([c, region, start, OPEN_END if last else versions[i + 1][2], 1 if last else 0])
    return [tuple([k + 1] + r) for k, r in enumerate(rows)]


def region_at(dim, customer_id, day):
    for _, cid, region, start, end, _ in dim:
        if cid == customer_id and start <= day < end:
            return region
    return "Unknown"


def region_now(dim, customer_id):
    for _, cid, region, _, _, current in dim:
        if cid == customer_id and current == 1:
            return region
    return "Unknown"


def ref_orders_with_region(tables, dim):
    return [(o["order_id"], o["customer_id"], o["order_date"], o["amount"],
             region_at(dim, o["customer_id"], o["order_date"]), region_now(dim, o["customer_id"]))
            for o in sorted(tables["orders"], key=lambda o: o["order_id"])]


def ref_revenue(tables, dim, current):
    groups = {}
    for o in tables["orders"]:
        region = region_now(dim, o["customer_id"]) if current else region_at(dim, o["customer_id"], o["order_date"])
        groups.setdefault(region, []).append(o["amount"])
    return [(r, len(groups[r]), round(sum(groups[r]), 2)) for r in sorted(groups)]


# ---- The checks ---------------------------------------------------------------

class ScdChecks:
    tables = None

    @classmethod
    def setUpClass(cls):
        cls.queries = load_queries(SQL_FILE)
        cls.dim = ref_type2(cls.tables)
        cls.con = sqlite3.connect(":memory:")
        for table, cols in TABLES.items():
            cls.con.execute("CREATE TABLE %s (%s)" % (table, ", ".join(cols)))
            cls.con.executemany("INSERT INTO %s VALUES (%s)" % (table, ", ".join("?" * len(cols))),
                                [[r[c] for c in cols] for r in cls.tables[table]])
        cls.con.execute("CREATE TABLE dim_customer (%s)" % ", ".join(DIM_COLUMNS))
        cls.con.executemany("INSERT INTO dim_customer VALUES (?, ?, ?, ?, ?, ?)", cls.dim)

    def run_query(self, name):
        sql = self.queries.get(name, "")
        if not sql:
            self.fail("query '%s' is empty in %s: write it first" % (name, os.path.basename(SQL_FILE)))
        return [tuple(r) for r in self.con.execute(sql).fetchall()]

    def assertRowsEqual(self, actual, expected, what):
        self.assertEqual(len(actual), len(expected),
                         "%s: got %d rows, expected %d" % (what, len(actual), len(expected)))
        for a, e in zip(actual, expected):
            self.assertEqual(len(a), len(e), "%s: row %r should have the columns of %r" % (what, a, e))
            for x, y in zip(a, e):
                if isinstance(y, float):
                    self.assertIsNotNone(x, "%s: got NULL in %r, expected %r" % (what, a, e))
                    self.assertAlmostEqual(x, y, delta=0.011, msg="%s: row %r, expected %r" % (what, a, e))
                else:
                    self.assertEqual(x, y, "%s: row %r, expected %r" % (what, a, e))

    def test_scd_type1(self):
        self.assertRowsEqual(self.run_query("scd_type1"), ref_type1(self.tables),
                             "scd_type1 (latest by changed_on, then change_id; a late entry has a high change_id "
                             "but an old date)")

    def test_scd_type2(self):
        actual = self.run_query("scd_type2")
        expected = self.dim
        if len(actual) > len(expected) and expected:
            self.fail("scd_type2: %d versions, expected %d. A save that keeps the same region, or a typo fixed the "
                      "same day, is not a new version" % (len(actual), len(expected)))
        self.assertRowsEqual(actual, expected, "scd_type2 (valid_from inclusive, valid_to = next valid_from, "
                                               "current row open to 9999-12-31)")

    def test_type2_windows_do_not_overlap(self):
        rows = self.run_query("scd_type2")
        by_customer = {}
        for r in rows:
            if len(r) == 6:
                by_customer.setdefault(r[1], []).append(r)
        for cid, versions in by_customer.items():
            for a, b in zip(versions, versions[1:]):
                self.assertEqual(a[4], b[3], "customer %s: a version must end on the day the next one starts "
                                             "(%r then %r)" % (cid, a, b))
            self.assertEqual(sum(v[5] for v in versions), 1, "customer %s needs exactly one current version" % cid)

    def test_orders_with_region(self):
        self.assertRowsEqual(self.run_query("orders_with_region"), ref_orders_with_region(self.tables, self.dim),
                             "orders_with_region (valid_from <= order_date < valid_to; no match is 'Unknown')")

    def test_revenue_by_region_as_ordered(self):
        actual = self.run_query("revenue_by_region_as_ordered")
        self.assertRowsEqual(actual, ref_revenue(self.tables, self.dim, current=False),
                             "revenue_by_region_as_ordered (join on the version valid on the order date)")
        self.assertEqual(sum(r[1] for r in actual), len(self.tables["orders"]),
                         "every order must be counted exactly once, including orders before the first record")

    def test_revenue_by_region_current(self):
        self.assertRowsEqual(self.run_query("revenue_by_region_current"), ref_revenue(self.tables, self.dim, True),
                             "revenue_by_region_current (join on is_current = 1)")


class TestCommittedData(ScdChecks, unittest.TestCase):
    tables = read_csv_tables()

    def test_data_has_the_traps(self):
        moved = {r[1] for r in self.dim if r[5] == 0}
        self.assertTrue(moved, "data should have customers who moved")
        self.assertIn("Unknown", [r[4] for r in ref_orders_with_region(self.tables, self.dim)],
                      "data should have orders before the first record")


class TestSecondDataset(ScdChecks, unittest.TestCase):
    """Built in memory with another seed: hard-coded answers fail here."""
    tables = tables_from_build(SECOND_SEED)


class TestTinyEdgeCases(ScdChecks, unittest.TestCase):
    """A: Coast, a new street (still Coast), then Lakes from 1 March; an order on
    exactly 1 March is a Lakes order. B: typed Alpine, corrected to Coast the same
    day, then a move to Lakes on 10 Feb that was entered late (highest change_id,
    but an earlier date than B's 20 Feb save, which says Coast again). C: one
    order before its first record. D: an order but no record at all, and 0.00."""
    tables = {
        "customer_changes": [
            {"change_id": 1, "customer_id": "A", "region": "Coast", "changed_on": "2025-01-01"},
            {"change_id": 2, "customer_id": "B", "region": "Alpine", "changed_on": "2025-01-05"},
            {"change_id": 3, "customer_id": "B", "region": "Coast", "changed_on": "2025-01-05"},
            {"change_id": 4, "customer_id": "A", "region": "Coast", "changed_on": "2025-02-01"},
            {"change_id": 5, "customer_id": "B", "region": "Coast", "changed_on": "2025-02-20"},
            {"change_id": 6, "customer_id": "A", "region": "Lakes", "changed_on": "2025-03-01"},
            {"change_id": 7, "customer_id": "C", "region": "Alpine", "changed_on": "2025-03-01"},
            {"change_id": 8, "customer_id": "B", "region": "Lakes", "changed_on": "2025-02-10"},
        ],
        "orders": [
            {"order_id": "O1", "customer_id": "A", "order_date": "2025-02-28", "amount": 10.0},
            {"order_id": "O2", "customer_id": "A", "order_date": "2025-03-01", "amount": 20.0},
            {"order_id": "O3", "customer_id": "B", "order_date": "2025-01-05", "amount": 30.0},
            {"order_id": "O4", "customer_id": "B", "order_date": "2025-02-15", "amount": 40.0},
            {"order_id": "O5", "customer_id": "C", "order_date": "2025-02-01", "amount": 50.0},
            {"order_id": "O6", "customer_id": "D", "order_date": "2025-02-02", "amount": 0.0},
        ],
    }

    def test_reference_reads_the_story(self):
        self.assertEqual([(r[1], r[2], r[3], r[4]) for r in self.dim],
                         [("A", "Coast", "2025-01-01", "2025-03-01"), ("A", "Lakes", "2025-03-01", OPEN_END),
                          ("B", "Coast", "2025-01-05", "2025-02-10"), ("B", "Lakes", "2025-02-10", "2025-02-20"),
                          ("B", "Coast", "2025-02-20", OPEN_END), ("C", "Alpine", "2025-03-01", OPEN_END)])


class TestEmptyTables(ScdChecks, unittest.TestCase):
    """No changes and no orders: every query returns no rows instead of an error."""
    tables = {"customer_changes": [], "orders": []}


if __name__ == "__main__":
    unittest.main()
