"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py."""
import importlib.util
import os
import sqlite3
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)

EXPECTED = {
    "Q1": "correct",
    "Q2": "wrong rows",
    "Q3": "error",
    "Q4": "correct",
    "Q5": "wrong rows",
    "Q6": "wrong rows",
    "Q7": "error",
    "Q8": "correct",
}


class TestCheckSql(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = lesson.load_db(os.path.join(HERE, "data"))

    def test_run_query_success(self):
        rows, err = lesson.run_query(self.conn, "SELECT COUNT(*) FROM customers")
        self.assertIsNone(err)
        self.assertEqual(rows, [(60,)])

    def test_run_query_error(self):
        rows, err = lesson.run_query(self.conn, "SELECT nope FROM customers")
        self.assertIsNone(rows)
        self.assertIn("nope", err)

    def test_normalize(self):
        self.assertEqual(lesson.normalize([("b", 2.004), ("a", 1)]), lesson.normalize([("a", 1), ("b", 2.0)]))
        self.assertNotEqual(lesson.normalize([("a", 1)]), lesson.normalize([("a", 2)]))

    def test_tiny_classify(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE t (x INTEGER)")
        conn.executemany("INSERT INTO t VALUES (?)", [(1,), (2,), (3,)])
        self.assertEqual(lesson.classify(conn, "SELECT x FROM t ORDER BY x DESC", "SELECT x FROM t"), "correct")
        self.assertEqual(lesson.classify(conn, "SELECT x FROM t WHERE x > 1", "SELECT x FROM t"), "wrong rows")
        self.assertEqual(lesson.classify(conn, "SELEC x FROM t", "SELECT x FROM t"), "error")

    def test_all_llm_queries(self):
        got = {q["query_id"]: lesson.classify(self.conn, q["llm_sql"], q["trusted_sql"])
               for q in lesson.load_queries(os.path.join(HERE, "data"))}
        self.assertEqual(got, EXPECTED)


if __name__ == "__main__":
    unittest.main()
