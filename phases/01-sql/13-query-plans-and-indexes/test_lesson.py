"""Tests for lesson 13: query plans and indexes.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

What is checked:
1. plan, full_scans and count_steps on tiny hand-made tables, against the
   test's own reading of EXPLAIN QUERY PLAN and its own step counter.
2. Your FAST_QUERIES give the same answers as a plain Python computation
   (never SQL) for several parameters, on the committed data, on a second
   dataset from make_data.build(seed=2027), and on hand-made edge cases:
   no orders, the first and last second of a day, a month that ends the year,
   two orders at the same second, a NULL time, a cancelled order and an
   order from a customer who is not in the customers table.
3. With DROP_INDEXES and CREATE_INDEXES applied to today's database, no tile
   has a SCAN line in its plan, and the work (steps) drops against the
   dashboard as it was before the status index, on both datasets.
"""
import importlib.util
import os
import sqlite3
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dashboard  # noqa: E402
import make_data  # noqa: E402

if os.environ.get("CHECK_SOLUTION") == "1":
    PY_FILE = os.path.join(HERE, "solution", "solution.py")
else:
    PY_FILE = os.path.join(HERE, "exercise.py")

SECOND_SEED = 2027
MAX_NEW_INDEXES = 3
TILES = ["customer_history", "day_summary", "city_month"]


def load_learner():
    spec = importlib.util.spec_from_file_location("learner", PY_FILE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


L = load_learner()


def as_loaded(tables):
    """Values exactly as they come back from the CSV files."""
    return {t: [{k: dashboard.cast(None if v is None else str(v)) for k, v in r.items()} for r in rows]
            for t, rows in tables.items()}


# The test's own tools, written separately from the learner's.

def ref_plan(con, sql, params=()):
    return [r[-1] for r in con.execute("EXPLAIN QUERY PLAN %s" % sql, params).fetchall()]


def ref_scans(lines):
    out = []
    for line in lines:
        if line.startswith("SCAN ") and line != "SCAN CONSTANT ROW":
            name = line[5:].split(" ")[0]
            if name not in out:
                out.append(name)
    return sorted(out)


def ref_steps(con, sql, params=()):
    n = [0]

    def cb():
        n[0] += 1
        return 0
    con.set_progress_handler(cb, 1)
    rows = con.execute(sql, params).fetchall()
    con.set_progress_handler(None, 1)
    return n[0], rows


# The tiles' answers, in plain Python.

def ref_tile(tables, tile, params):
    orders = tables["orders"]
    if tile == "customer_history":
        mine = [o for o in orders if o["customer_id"] == params["customer_id"]]
        mine.sort(key=lambda o: ((o["ordered_at"] or ""), o["order_id"]), reverse=True)
        # SQLite sorts NULL first ascending, so last descending: a NULL time goes to the end.
        mine.sort(key=lambda o: o["ordered_at"] is None)
        return [(o["order_id"], o["ordered_at"], o["amount"], o["status"]) for o in mine[:10]]
    if tile == "day_summary":
        hits = [o["amount"] for o in orders if o["status"] == "completed"
                and o["ordered_at"] is not None and o["ordered_at"][:10] == params["day"]]
        return [(len(hits), sum(hits) if hits else None)]
    city = {c["customer_id"]: c["city"] for c in tables["customers"]}
    per = {}
    for o in orders:
        if o["status"] != "completed" or o["ordered_at"] is None or o["customer_id"] not in city:
            continue
        if o["ordered_at"][:7] != params["month"]:
            continue
        s = per.setdefault(city[o["customer_id"]], [0, 0])
        s[0] += 1
        s[1] += o["amount"]
    return sorted([(c, n, r) for c, (n, r) in per.items()], key=lambda r: (-r[2], r[0]))


def improved_db(tables):
    con = dashboard.open_db(tables)
    existing = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'index'")}
    for name in L.DROP_INDEXES:
        if name not in existing:
            raise AssertionError("DROP_INDEXES: there is no index called %r; the existing ones are %s"
                                 % (name, sorted(existing)))
        con.execute("DROP INDEX %s" % name)
    for sql in L.CREATE_INDEXES:
        con.execute(sql)
    return con


class TestPlanTools(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        self.con.execute("CREATE TABLE t (a, b)")
        self.con.execute("CREATE TABLE u (k, v)")
        self.con.executemany("INSERT INTO t VALUES (?, ?)", [(i % 7, i) for i in range(60)])
        self.con.executemany("INSERT INTO u VALUES (?, ?)", [(i, "x%d" % i) for i in range(7)])

    def test_plan(self):
        for sql, params in [("SELECT * FROM t WHERE a = ?", (3,)),
                            ("SELECT a, COUNT(*) FROM t GROUP BY a ORDER BY 2 DESC", ()),
                            ("SELECT * FROM t x JOIN u y ON y.k = x.a WHERE x.b > :m", {"m": 10})]:
            self.assertEqual(L.plan(self.con, sql, params), ref_plan(self.con, sql, params),
                             "plan: return the detail text (the last column) of every EXPLAIN QUERY PLAN row, "
                             "in order, for %s" % sql)

    def test_full_scans_without_and_with_index(self):
        sql = "SELECT b FROM t WHERE a = ?"
        self.assertEqual(L.full_scans(self.con, sql, (3,)), ["t"],
                         "full_scans: with no index, the plan says SCAN t, so the answer is ['t']")
        self.con.execute("CREATE INDEX ix_t_a ON t (a)")
        self.assertEqual(L.full_scans(self.con, sql, (3,)), [],
                         "full_scans: with an index on a, the plan says SEARCH t, so nothing is scanned")
        sql = "SELECT a FROM t ORDER BY a"
        self.assertEqual(L.full_scans(self.con, sql), ref_scans(ref_plan(self.con, sql)),
                         "full_scans: SCAN t USING COVERING INDEX still reads every entry, so t counts")

    def test_full_scans_join_and_no_table(self):
        sql = "SELECT * FROM t x JOIN u y ON y.v = x.b"
        self.assertEqual(L.full_scans(self.con, sql), ref_scans(ref_plan(self.con, sql)),
                         "full_scans: use the names exactly as the plan prints them (here the aliases)")
        self.assertEqual(L.full_scans(self.con, "SELECT 1"), [],
                         "full_scans: SCAN CONSTANT ROW is a SELECT with no table, not a scan of a table")

    def assertSteps(self, got, expected, msg):
        # Python keeps prepared statements in a cache, so the first run of a new statement can cost one
        # step more than the next run. Allow that much.
        self.assertIsInstance(got, int, "count_steps: return a whole number, got %r" % (got,))
        self.assertLessEqual(abs(got - expected), 2, "%s (got %d, expected %d)" % (msg, got, expected))

    def test_count_steps(self):
        sql = "SELECT SUM(b) FROM t WHERE a = :a"
        expected, _ = ref_steps(self.con, sql, {"a": 2})
        self.assertSteps(L.count_steps(self.con, sql, {"a": 2}), expected,
                         "count_steps: set the progress handler with N = 1, count every call, run to the end")
        self.con.execute("CREATE TABLE empty (a)")
        expected, _ = ref_steps(self.con, "SELECT * FROM empty")
        self.assertSteps(L.count_steps(self.con, "SELECT * FROM empty"), expected,
                         "count_steps: an empty table still costs a few steps; count them the same way")
        self.con.execute("CREATE INDEX ix_t_a ON t (a)")
        with_index, _ = ref_steps(self.con, sql, {"a": 2})
        self.assertSteps(L.count_steps(self.con, sql, {"a": 2}), with_index,
                         "count_steps: give the count again after the index exists; do not cache it")


class DashboardCase(unittest.TestCase):
    def setUp(self):
        for tile in TILES:
            if not str(L.FAST_QUERIES.get(tile, "")).strip():
                self.fail("FAST_QUERIES['%s'] is empty: write the tile's query first" % tile)

    def run_tile(self, con, tile, params):
        try:
            return [tuple(r) for r in con.execute(L.FAST_QUERIES[tile], params).fetchall()]
        except sqlite3.Error as e:
            self.fail("FAST_QUERIES['%s'] did not run: %s" % (tile, e))

    def check_answers(self, tables, cases, where):
        con = improved_db(tables)
        for tile, params in cases:
            got = self.run_tile(con, tile, params)
            exp = ref_tile(tables, tile, params)
            self.assertEqual(got, exp, "%s, %s with %r: got %r, expected %r"
                             % (where, tile, params, got[:3], exp[:3]))

    def check_speed(self, tables, where):
        before = dashboard.open_db(tables, indexes=[])  # the dashboard before the status index
        after = improved_db(tables)
        self.assertLessEqual(len(L.CREATE_INDEXES), MAX_NEW_INDEXES,
                             "CREATE_INDEXES: at most %d new indexes; every index slows down every new order"
                             % MAX_NEW_INDEXES)
        for tile in TILES:
            params = dashboard.EXAMPLE_PARAMS[tile]
            lines = ref_plan(after, L.FAST_QUERIES[tile], params)
            scans = [x for x in lines if x.startswith("SCAN")]
            self.assertFalse(scans, "%s, %s: the plan still has %s; every table should be reached by SEARCH"
                             % (where, tile, scans))
            old, _ = ref_steps(before, dashboard.QUERIES[tile], params)
            new, _ = ref_steps(after, L.FAST_QUERIES[tile], params)
            limit = old * 0.75 if tile == "city_month" else old / 10.0
            self.assertLessEqual(new, limit, "%s, %s: %d steps, the old dashboard took %d; aim for at most %d. "
                                 "Read the plan: which index does it pick?" % (where, tile, new, old, limit))


class TestCommittedData(DashboardCase):
    def test_answers(self):
        tables = dashboard.read_csv_tables()
        cases = [("customer_history", {"customer_id": c}) for c in ["T00007", "T00300", "T99999"]]
        cases += [("day_summary", {"day": d}) for d in ["2026-10-17", "2026-07-01", "2026-11-05"]]
        cases += [("city_month", {"month": m}) for m in ["2026-10", "2026-07", "2026-12"]]
        self.check_answers(tables, cases, "committed data")

    def test_speed(self):
        self.check_speed(dashboard.read_csv_tables(), "committed data")


class TestSecondDataset(DashboardCase):
    def test_answers_and_speed(self):
        tables = as_loaded(make_data.build(seed=SECOND_SEED))
        cases = [("customer_history", {"customer_id": c}) for c in ["T00003", "T00150"]]
        cases += [("day_summary", {"day": d}) for d in ["2026-08-15", "2026-10-31"]]
        cases += [("city_month", {"month": m}) for m in ["2026-08", "2026-09"]]
        self.check_answers(tables, cases, "second dataset (seed %d)" % SECOND_SEED)
        self.check_speed(tables, "second dataset (seed %d)" % SECOND_SEED)


def small(orders, customers=None):
    customers = customers if customers is not None else [
        {"customer_id": "A", "city": "Pune", "joined_on": "2026-01-01"},
        {"customer_id": "B", "city": "Nagpur", "joined_on": "2026-01-01"}]
    return {"customers": customers,
            "orders": [{"order_id": o[0], "customer_id": o[1], "ordered_at": o[2], "amount": o[3],
                        "status": o[4] if len(o) > 4 else "completed"} for o in orders]}


class TestEdgeCases(DashboardCase):
    def test_empty(self):
        self.check_answers(small([]), [("customer_history", {"customer_id": "A"}),
                                       ("day_summary", {"day": "2026-10-17"}),
                                       ("city_month", {"month": "2026-10"})],
                           "no orders (one row with 0 orders and NULL revenue for the day tile)")

    def test_day_bounds(self):
        d = small([(1, "A", "2026-10-16 23:59:59", 100), (2, "A", "2026-10-17 00:00:00", 200),
                   (3, "A", "2026-10-17 23:59:59", 300), (4, "A", "2026-10-18 00:00:00", 400)])
        self.check_answers(d, [("day_summary", {"day": "2026-10-17"})],
                           "orders 2 and 3 are on 17 October; 1 and 4 are not")

    def test_year_end(self):
        d = small([(1, "A", "2026-12-31 23:59:59", 100), (2, "B", "2027-01-01 00:00:00", 200),
                   (3, "A", "2026-12-01 00:00:00", 50), (4, "B", "2026-11-30 23:59:59", 70)])
        self.check_answers(d, [("city_month", {"month": "2026-12"}), ("day_summary", {"day": "2026-12-31"})],
                           "December 2026 ends at 2027-01-01 00:00:00, not at 2026-13-01")

    def test_same_second(self):
        d = small([(5, "A", "2026-10-01 12:00:00", 100), (9, "A", "2026-10-01 12:00:00", 200),
                   (7, "A", "2026-10-01 12:00:00", 300), (1, "A", "2026-09-01 12:00:00", 400)])
        self.check_answers(d, [("customer_history", {"customer_id": "A"})],
                           "three orders at the same second come newest order_id first: 9, 7, 5, then 1")

    def test_null_cancelled_and_unknown_customer(self):
        d = small([(1, "A", None, 100), (2, "A", "2026-10-05 10:00:00", 200, "cancelled"),
                   (3, "Z", "2026-10-05 11:00:00", 300), (4, "B", "2026-10-05 12:00:00", 400)])
        self.check_answers(d, [("customer_history", {"customer_id": "A"}),
                               ("day_summary", {"day": "2026-10-05"}),
                               ("city_month", {"month": "2026-10"})],
                           "a NULL time is on no day; a cancelled order does not count; customer Z is not in "
                           "customers, so the month tile (an inner join) leaves order 3 out")


if __name__ == "__main__":
    unittest.main()
