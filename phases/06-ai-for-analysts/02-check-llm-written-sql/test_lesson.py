"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py."""
import importlib.util
import os
import sqlite3
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lesson = load("lesson", TARGET)
make_data = load("make_data", os.path.join(HERE, "make_data.py"))
DATA = os.path.join(HERE, "data")
OTHER_SEED = 77

# Labels on the two committed databases. Q9 and Q10 are right on database 1 by accident.
EXPECTED = {
    "Q1": "correct",
    "Q2": "wrong rows",
    "Q3": "error",
    "Q4": "correct",
    "Q5": "wrong rows",
    "Q6": "wrong rows",
    "Q7": "error",
    "Q8": "correct",
    "Q9": "wrong rows",
    "Q10": "wrong rows",
    "Q11": "wrong rows",
    "Q12": "blocked",
}


def tiny_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE t (x INTEGER, y TEXT)")
    conn.executemany("INSERT INTO t VALUES (?, ?)", [(1, "a"), (2, "b"), (3, "c")])
    return conn


def reference_answers(tables):
    """Plain-Python answers to some of the questions, with no SQL at all."""
    customers, orders = tables["customers"], tables["orders"]
    country = dict(customers)
    completed = [o for o in orders if o[3] == "completed"]
    per_country = {}
    for _, c in customers:
        per_country[c] = per_country.get(c, 0) + 1
    ordered_ids = {o[1] for o in orders}
    completed_ids = {o[1] for o in completed}
    revenue = {}
    for o in completed:
        if o[1] is not None:
            revenue[country[o[1]]] = revenue.get(country[o[1]], 0.0) + o[4]
    return {
        "Q1": [(round(sum(o[4] for o in completed), 2),)],
        "Q2": sorted(per_country.items()),
        "Q5": sorted((cid,) for cid, _ in customers if cid not in ordered_ids),
        "Q9": sorted((cid,) for cid, _ in customers if cid not in completed_ids),
        "Q10": [(sum(1 for o in orders if o[3] in ("refunded", "cancelled")),)],
        "Q11": [(c, round(v, 2)) for c, v in sorted(revenue.items(), key=lambda kv: -kv[1])],
    }


class TestGuard(unittest.TestCase):
    def test_allows_single_reads(self):
        for sql in ["SELECT 1", "select 1;", "SELECT ';' AS s", "-- note\nSELECT 1",
                    "WITH x AS (SELECT 1) SELECT * FROM x", "SELECT replace(country, 'U', 'u') FROM customers"]:
            self.assertIsNone(lesson.guard(sql), "guard should allow %r" % sql)

    def test_refuses_writes_and_stacked_statements(self):
        for sql in ["DELETE FROM orders", "SELECT 1; DROP TABLE orders", "WITH x AS (SELECT 1) DELETE FROM orders",
                    "PRAGMA query_only = OFF", "ATTACH DATABASE 'x.db' AS x", "UPDATE orders SET amount = 0",
                    "", "  ;  "]:
            self.assertIsNotNone(lesson.guard(sql), "guard should refuse %r" % sql)

    def test_connection_is_read_only_even_without_the_guard(self):
        conn = lesson.load_db(DATA)
        with self.assertRaises(sqlite3.OperationalError):
            conn.execute("DELETE FROM orders")
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM orders").fetchall(), [(300,)])


class TestRunQuery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = lesson.load_db(DATA)

    def test_run_query_success(self):
        rows, err = lesson.run_query(self.conn, "SELECT COUNT(*) FROM customers")
        self.assertIsNone(err)
        self.assertEqual(rows, [(60,)])

    def test_run_query_error(self):
        rows, err = lesson.run_query(self.conn, "SELECT nope FROM customers")
        self.assertIsNone(rows)
        self.assertIn("nope", err)

    def test_row_cap(self):
        rows, err = lesson.run_query(self.conn, "SELECT * FROM orders", max_rows=10)
        self.assertIsNone(rows, "300 rows with max_rows=10 should be refused, not cut short")
        self.assertIsNotNone(err)
        rows, err = lesson.run_query(self.conn, "SELECT * FROM orders", max_rows=300)
        self.assertEqual(len(rows), 300, "exactly max_rows rows is allowed")

    def test_time_limit(self):
        slow = "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c LIMIT 20000000) SELECT COUNT(*) FROM c"
        start = time.monotonic()
        rows, err = lesson.run_query(self.conn, slow, max_seconds=0.2)
        self.assertIsNone(rows, "a query past max_seconds should return an error: use set_progress_handler")
        self.assertLess(time.monotonic() - start, 1.0)
        rows, err = lesson.run_query(self.conn, "SELECT 1")
        self.assertEqual(rows, [(1,)], "remove the progress handler after each query")


class TestCompare(unittest.TestCase):
    def test_tolerance_and_row_order(self):
        self.assertTrue(lesson.same_result([("b", 2.004), ("a", 1)], [("a", 1), ("b", 2.0)]))
        self.assertFalse(lesson.same_result([("a", 1)], [("a", 2)]))
        # rounding to 2 places would split these (2.0 vs 2.01); a tolerance does not
        self.assertTrue(lesson.same_result([(2.004,)], [(2.006,)]))
        self.assertFalse(lesson.same_result([(120.93,)], [(120.92,)]), "a cent apart is a different number")

    def test_ordered(self):
        self.assertFalse(lesson.same_rows([(2,), (1,)], [(1,), (2,)], True))
        self.assertTrue(lesson.same_rows([(2,), (1,)], [(1,), (2,)], False))
        self.assertFalse(lesson.same_result([(2,), (1,)], [(1,), (2,)], ordered=True),
                         "when order is the answer, a reversed list is wrong")

    def test_duplicates_count(self):
        self.assertFalse(lesson.same_rows([(1,), (1,), (2,)], [(1,), (2,), (2,)], False),
                         "the same set of distinct rows is not enough: duplicates must match too")

    def test_column_order_and_shape(self):
        self.assertTrue(lesson.same_result([(3, "US"), (5, "UK")], [("UK", 5), ("US", 3)]),
                        "SELECT COUNT(*), country answers the same question as SELECT country, COUNT(*)")
        self.assertFalse(lesson.same_result([("US", 3, 1)], [("US", 3)]), "an extra column is a different result")

    def test_empty_and_null(self):
        self.assertTrue(lesson.same_result([], []))
        self.assertFalse(lesson.same_result([], [(1,)]))
        self.assertFalse(lesson.same_result([(1,)], []))
        self.assertTrue(lesson.same_result([(None,)], [(None,)]))
        self.assertFalse(lesson.same_result([(None,)], [(0,)]), "NULL is not zero")


class TestClassify(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dbs = lesson.load_dbs(DATA)
        cls.queries = {q["query_id"]: q for q in lesson.load_queries(DATA)}

    def test_tiny_classify(self):
        conn = tiny_conn()
        self.assertEqual(lesson.classify(conn, "SELECT x FROM t ORDER BY x DESC", "SELECT x FROM t"), "correct")
        self.assertEqual(lesson.classify(conn, "SELECT x FROM t WHERE x > 1", "SELECT x FROM t"), "wrong rows")
        self.assertEqual(lesson.classify(conn, "SELECT x FRM t", "SELECT x FROM t"), "error")
        # a misspelt first word is not on the allowlist, so it never reaches the database
        self.assertEqual(lesson.classify(conn, "SELEC x FROM t", "SELECT x FROM t"), "blocked")
        self.assertEqual(lesson.classify(conn, "SELECT x FROM t ORDER BY x", "SELECT x FROM t ORDER BY x DESC"), "wrong rows")
        self.assertEqual(lesson.classify(conn, "DELETE FROM t", "SELECT x FROM t"), "blocked")
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM t").fetchall(), [(3,)], "a blocked query must never run")

    def test_all_llm_queries(self):
        got = {qid: lesson.classify(self.dbs, q["llm_sql"], q["trusted_sql"]) for qid, q in self.queries.items()}
        self.assertEqual(got, EXPECTED)

    def test_one_database_is_not_enough(self):
        q = self.queries["Q9"]
        self.assertEqual(lesson.classify(self.dbs[0], q["llm_sql"], q["trusted_sql"]), "correct",
                         "on database 1 alone the NOT IN query looks right")
        self.assertEqual(lesson.classify(self.dbs, q["llm_sql"], q["trusted_sql"]), "wrong rows",
                         "database 2 has guest orders with no customer_id, which break NOT IN")

    def test_second_seed_against_plain_python(self):
        tables = make_data.build(seed=OTHER_SEED, awkward=True)
        new_db = lesson.make_db(tables)
        reference = reference_answers(tables)
        for qid, want in reference.items():
            rows, err = lesson.run_query(new_db, self.queries[qid]["trusted_sql"])
            self.assertIsNone(err)
            got = [tuple(round(v, 2) if isinstance(v, float) else v for v in r) for r in rows]
            if qid != "Q11":
                got = sorted(got)
            self.assertEqual(got, want, "seed %d: trusted %s does not match plain Python" % (OTHER_SEED, qid))
        got = {qid: lesson.classify([self.dbs[0], new_db], q["llm_sql"], q["trusted_sql"])
               for qid, q in self.queries.items()}
        self.assertEqual(got, EXPECTED, "seed %d: labels on a fresh awkward database" % OTHER_SEED)
        rows, _ = lesson.run_query(new_db, self.queries["Q9"]["llm_sql"])
        self.assertEqual(rows, [], "NOT IN over a column with a NULL returns nothing")
        self.assertTrue(reference["Q9"], "yet some customers never had a completed order")


if __name__ == "__main__":
    unittest.main()
