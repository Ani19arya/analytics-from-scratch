"""Tests for lesson 12: review a query someone else wrote.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

The expected slide is computed with plain Python loops, never with SQL. Your
fixed_slide query runs on three kinds of data:
1. the committed data/*.csv,
2. a second dataset built in memory with make_data.build(seed=2026), so a
   query that just types out the answers cannot pass,
3. tiny hand-made tables for the edge cases: no orders, the first and last
   second of October and the first second of November, an order with three
   item lines, orders with no promo, a staff promo and a promo with no channel
   (NULL), an average that is not a whole number, and a city whose only order
   used a staff code (zero orders left).
Your findings are checked against the bugs planted in slide_query.sql.
"""
import csv
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

TABLES = {"customers": ["customer_id", "city"],
          "orders": ["order_id", "customer_id", "ordered_at", "amount", "status"],
          "order_items": ["order_id", "line_no", "item", "qty"],
          "promo_redemptions": ["order_id", "promo_code", "channel"]}
SECOND_SEED = 2026
PLANTED = {"FANOUT", "LEFT_JOIN_FILTER", "INTEGER_DIVISION", "DATE_BOUND"}
NOT_BUGS = {"STATUS_FILTER", "COUNT_DISTINCT", "MISSING_GROUP_BY", "CROSS_JOIN"}
WHY = {
    "FANOUT": "SUM(o.amount) runs after the join to order_items, so an order with 3 item lines counts 3 times",
    "LEFT_JOIN_FILTER": "p.channel <> 'staff' is NULL, not true, for an order with no promo, so WHERE drops it",
    "INTEGER_DIVISION": "SUM(o.amount) / COUNT(...) divides two whole numbers, so 525.87 becomes 525",
    "DATE_BOUND": "BETWEEN '2026-10-01' AND '2026-10-31' ends at 31 October 00:00:00 and misses that whole day",
    "STATUS_FILTER": "completed orders only is what Meher asked for",
    "COUNT_DISTINCT": "COUNT(DISTINCT o.order_id) is the one count in the query that the fan-out cannot inflate",
    "MISSING_GROUP_BY": "city is the only column that is not inside an aggregate, and it is in GROUP BY",
    "CROSS_JOIN": "every join in the query has an ON condition",
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


# The reference answer, in plain Python.

def ref_fixed_slide(d):
    city = {c["customer_id"]: c["city"] for c in d["customers"]}
    items = {}
    for i in d["order_items"]:
        items[i["order_id"]] = items.get(i["order_id"], 0) + i["qty"]
    staff = {p["order_id"] for p in d["promo_redemptions"] if p["channel"] == "staff"}
    per_city = {}
    for o in d["orders"]:
        if o["status"] != "completed" or o["order_id"] in staff or o["customer_id"] not in city:
            continue
        if not ("2026-10-01 00:00:00" <= o["ordered_at"] < "2026-11-01 00:00:00"):
            continue
        s = per_city.setdefault(city[o["customer_id"]], [0, 0, 0])
        s[0] += 1
        s[1] += items.get(o["order_id"], 0)
        s[2] += o["amount"]
    rows = [(c, n, it, rev, round2(rev / n), round2(it / n)) for c, (n, it, rev) in per_city.items()]
    return sorted(rows, key=lambda r: (-r[3], r[0]))


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

    def check_slide(self, d, where):
        self.assertRowsEqual(self.run_query(make_db(d), "fixed_slide"), ref_fixed_slide(d), where + ", fixed_slide")


class TestCommittedData(SqlTestCase):
    def setUp(self):
        self.d = {t: read_csv(t) for t in TABLES}

    def test_fixed_slide(self):
        got = self.run_query(make_db(self.d), "fixed_slide")
        expected = ref_fixed_slide(self.d)
        self.assertEqual(sum(r[1] for r in got), sum(r[1] for r in expected),
                         "the orders on your slide should add up to %d, the completed October orders without a "
                         "staff code; count them straight from the orders table to check"
                         % sum(r[1] for r in expected))
        self.assertRowsEqual(got, expected, "fixed_slide")

    def test_slide_query_is_still_wrong(self):
        """The planted query must keep giving a different answer, or the lesson has nothing to find."""
        with open(os.path.join(HERE, "slide_query.sql")) as f:
            original = [tuple(r) for r in make_db(self.d).execute(f.read()).fetchall()]
        self.assertNotEqual(original, ref_fixed_slide(self.d),
                            "slide_query.sql should be Rahul's original query with its bugs; do not edit it")


class TestFindings(SqlTestCase):
    def test_findings(self):
        rows = self.run_query(make_db({}), "findings")
        codes = {str(r[0]).strip().upper() for r in rows if r and r[0] is not None}
        unknown = codes - PLANTED - NOT_BUGS
        self.assertFalse(unknown, "findings: %s is not on the list of codes in exercise.sql" % sorted(unknown))
        for code in sorted(codes & NOT_BUGS):
            self.fail("findings: %s is not a bug in slide_query.sql: %s" % (code, WHY[code]))
        for code in sorted(PLANTED - codes):
            self.fail("findings: one bug is missing. Look again at this: %s" % WHY[code])


class TestSecondDataset(SqlTestCase):
    def test_same_query_on_new_data(self):
        d = {t: as_loaded(rows) for t, rows in make_data.build(seed=SECOND_SEED).items()}
        self.check_slide(d, "second dataset (seed %d)" % SECOND_SEED)


def tables(orders, items=None, promos=(), customers=None):
    """orders: list of (order_id, customer_id, ordered_at, amount[, status]); one item line of qty 1 per order
    unless items is given as a list of (order_id, qty)."""
    customers = customers or [{"customer_id": "A", "city": "Pune"}, {"customer_id": "B", "city": "Nagpur"}]
    o_rows = [{"order_id": o[0], "customer_id": o[1], "ordered_at": o[2], "amount": o[3],
               "status": o[4] if len(o) > 4 else "completed"} for o in orders]
    if items is None:
        items = [(o[0], 1) for o in orders]
    i_rows = [{"order_id": oid, "line_no": n, "item": "Poha", "qty": q} for n, (oid, q) in enumerate(items, 1)]
    p_rows = [{"order_id": oid, "promo_code": "X", "channel": ch} for oid, ch in promos]
    return {"customers": customers, "orders": o_rows, "order_items": i_rows, "promo_redemptions": p_rows}


class TestEdgeCases(SqlTestCase):
    def test_empty(self):
        self.check_slide(tables([]), "no orders (the slide has no rows)")

    def test_date_bounds(self):
        d = tables([(1, "A", "2026-09-30 23:59:59", 100), (2, "A", "2026-10-01 00:00:00", 200),
                    (3, "A", "2026-10-31 21:15:00", 300), (4, "A", "2026-11-01 00:00:00", 400)])
        self.check_slide(d, "orders 2 (1 Oct 00:00:00) and 3 (31 Oct 21:15) are in October; 1 (30 Sep) and "
                            "4 (1 Nov 00:00:00) are not")

    def test_three_item_lines(self):
        d = tables([(1, "A", "2026-10-05 13:00:00", 500)], items=[(1, 2), (1, 1), (1, 3)])
        self.check_slide(d, "one order of 500 with three item lines is 1 order, 6 items and revenue 500, not 1500")

    def test_promos(self):
        d = tables([(1, "A", "2026-10-05 13:00:00", 100), (2, "A", "2026-10-05 14:00:00", 200),
                    (3, "A", "2026-10-05 15:00:00", 300), (4, "A", "2026-10-05 16:00:00", 400)],
                   promos=[(2, "app"), (3, "staff"), (4, None)])
        self.check_slide(d, "order 1 has no promo and order 4 a promo with no channel: both stay; only order 3, "
                            "the staff code, goes")

    def test_not_a_whole_number(self):
        d = tables([(1, "A", "2026-10-05 13:00:00", 100), (2, "A", "2026-10-06 13:00:00", 101)],
                   items=[(1, 1), (2, 2)])
        self.check_slide(d, "revenue 201 over 2 orders is 100.5, and 3 items over 2 orders is 1.5: divide as "
                            "decimals")

    def test_cancelled_and_only_staff(self):
        d = tables([(1, "A", "2026-10-05 13:00:00", 100), (2, "A", "2026-10-06 13:00:00", 900, "cancelled"),
                    (3, "B", "2026-10-07 13:00:00", 250)], promos=[(3, "staff")])
        self.check_slide(d, "the cancelled order does not count, and Nagpur's only order used a staff code, so "
                            "Nagpur is not on the slide")


if __name__ == "__main__":
    unittest.main()
