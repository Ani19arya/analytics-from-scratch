"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py.

Every allowed query's rows are recomputed here on an ordinary connection, and the database
file is hashed before and after every query run, so a gateway that lets a write through fails.
"""
import hashlib
import importlib.util
import os
import shutil
import sqlite3
import tempfile
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

OTHER_SEED = 1610
CAP = 500


def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class GatewayCase(unittest.TestCase):
    tables = None

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="w6-nl2sql-")
        cls.path = os.path.join(cls.tmp, "shop.db")
        lesson.build_db(cls.path, cls.tables if cls.tables is not None else lesson.load_tables())
        cls.hash = file_hash(cls.path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def reference_rows(self, sql):
        conn = sqlite3.connect(self.path)
        try:
            return conn.execute(sql).fetchall()
        finally:
            conn.close()

    def run_and_check_file(self, sql, **kw):
        result = lesson.run_question(self.path, sql, **kw)
        self.assertEqual(file_hash(self.path), self.hash, "the database file changed after running %r" % sql[:60])
        return result

    def check_questions(self, questions, label):
        for q in questions:
            result = self.run_and_check_file(q["llm_sql"])
            self.assertEqual(result["status"], q["expected_status"],
                             "%s %s (%s): expected %s, got %s (%s)" % (label, q["question_id"], q["why"],
                                                                      q["expected_status"], result["status"], result["reason"]))
            if q["expected_status"] in ("ok", "truncated"):
                want = self.reference_rows(q["llm_sql"])
                self.assertEqual(result["rows"], want[:CAP], "%s %s: rows differ from running the query directly" % (label, q["question_id"]))
                self.assertEqual(result["status"] == "truncated", len(want) > CAP)
            else:
                self.assertIsNone(result["rows"], "%s %s: a refused query must return rows None" % (label, q["question_id"]))
                self.assertTrue(result["reason"], "%s %s: say why it was refused" % (label, q["question_id"]))


class TestParsing(unittest.TestCase):
    def test_count_statements(self):
        cases = [
            ("SELECT 1", 1), ("SELECT 1;", 1), ("SELECT 1;  \n", 1), ("", 0), ("   ", 0), (";;", 0),
            ("-- only a comment", 0), ("SELECT 1; SELECT 2", 2), ("SELECT ';'", 1),
            ("SELECT 1 -- ; DROP TABLE t", 1), ("SELECT 1 /* ; */", 1), ("SELECT 'it''s; fine'", 1),
            ('SELECT "a;b" FROM t', 1), ("SELECT 1;\nDELETE FROM t;", 2), ("SELECT 1; -- bye", 1),
            ("SELECT [x;y] FROM t", 1), ("SELECT 1;;SELECT 2", 2),
        ]
        for sql, want in cases:
            self.assertEqual(lesson.count_statements(sql), want,
                             "%r holds %d statement(s): a ; inside quotes or comments does not count" % (sql, want))

    def test_first_keyword(self):
        cases = [("select 1", "SELECT"), ("  -- note\n with x as (select 1) select * from x", "WITH"),
                 ("/* hi */DELETE FROM t", "DELETE"), ("", ""), ("-- nothing", ""), ("PRAGMA table_info(t)", "PRAGMA")]
        for sql, want in cases:
            self.assertEqual(lesson.first_keyword(sql), want, "first keyword of %r should be %r" % (sql, want))


class TestWalls(GatewayCase):
    def test_readonly_connection_refuses_writes(self):
        conn = lesson.open_readonly(self.path)
        try:
            for sql in ["DELETE FROM orders", "CREATE TABLE x (a)", "UPDATE customers SET name = 'x'"]:
                with self.assertRaises(sqlite3.Error, msg="the read-only connection ran %r" % sql):
                    conn.execute(sql)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
                             self.reference_rows("SELECT COUNT(*) FROM customers")[0][0])
        finally:
            conn.close()
        self.assertEqual(file_hash(self.path), self.hash)

    def test_authorizer_alone(self):
        conn = sqlite3.connect(self.path)
        reasons = []
        conn.set_authorizer(lesson.make_authorizer(reasons))
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
                             self.reference_rows("SELECT COUNT(*) FROM orders")[0][0])
            self.assertEqual(reasons, [])
            for sql, word in [("SELECT email FROM customers", "email"), ("SELECT * FROM staff_pay", "staff_pay"),
                              ("DELETE FROM orders", "DELETE")]:
                del reasons[:]
                with self.assertRaises(sqlite3.Error, msg="the authorizer allowed %r" % sql):
                    conn.execute(sql)
                self.assertTrue(any(word in r for r in reasons), "no reason mentioning %s was recorded for %r" % (word, sql))
        finally:
            conn.close()

    def test_hand_made_queries(self):
        blocked = [
            "", "SELECT 1; SELECT 2", "WITH staff_pay AS (SELECT 1 AS x) SELECT * FROM main.staff_pay",
            "SELECT name FROM customers WHERE customer_id IN (SELECT staff_id FROM staff_pay)",
            "select lower(email) from customers", "INSERT INTO orders (order_id) VALUES (99999)",
            "WITH x AS (SELECT 1) UPDATE orders SET amount = 0",
        ]
        for sql in blocked:
            result = self.run_and_check_file(sql)
            self.assertEqual(result["status"], "blocked", "%r should be blocked, got %s" % (sql, result["status"]))
        ok = ["select count(*) from customers", "WITH t AS (SELECT amount FROM orders) SELECT COUNT(*) FROM t",
              "SELECT COUNT(*) FROM customers WHERE name = 'a;b'"]
        for sql in ok:
            result = self.run_and_check_file(sql)
            self.assertEqual(result["status"], "ok", "%r is a safe read, got %s (%s)" % (sql, result["status"], result["reason"]))
            self.assertEqual(result["rows"], self.reference_rows(sql))

    def test_caps(self):
        result = self.run_and_check_file("SELECT order_id FROM orders", max_rows=2000)
        self.assertEqual(result["status"], "ok", "with a cap above the row count nothing is truncated")
        result = self.run_and_check_file("SELECT order_id FROM orders ORDER BY order_id", max_rows=10)
        self.assertEqual(result["status"], "truncated")
        self.assertEqual(result["rows"], self.reference_rows("SELECT order_id FROM orders ORDER BY order_id")[:10])
        result = self.run_and_check_file("SELECT order_id FROM orders WHERE 0")
        self.assertEqual((result["status"], result["rows"]), ("ok", []), "an empty result is ok, not an error")
        result = self.run_and_check_file("WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n) SELECT MAX(i) FROM n",
                                         max_seconds=0.2)
        self.assertEqual(result["status"], "timeout", "a query that never ends must be stopped by the time limit")


class TestCommittedQuestions(GatewayCase):
    def test_every_question(self):
        self.check_questions(lesson.load_questions(), "committed data")


SECOND = make_data.build(seed=OTHER_SEED)


class TestSecondDataset(GatewayCase):
    tables = {name: [{k: str(v) for k, v in row.items()} for row in SECOND[name]] for name in ["customers", "orders", "staff_pay"]}

    def test_every_question(self):
        self.check_questions(SECOND["questions"], "seed %d" % OTHER_SEED)


if __name__ == "__main__":
    unittest.main()
