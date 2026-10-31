"""Tests for lesson 00-01: run your first lesson.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

The expected answers are worked out here in plain Python, from the data,
never copied from the solution.
"""
import csv
import importlib.util
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_data  # noqa: E402

if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)

SECOND_SEED = 2


def committed_orders():
    with open(os.path.join(HERE, "data", "orders.csv"), newline="") as f:
        rows = list(csv.DictReader(f))
    return [dict(r, amount=float(r["amount"])) for r in rows]


def built_orders(seed):
    return [dict(r, amount=float(r["amount"])) for r in make_data.build(seed)["orders"]]


def expected(orders):
    """A second, independent way to get the answers."""
    n, total = 0, 0.0
    for order in orders:
        n += 1
        total += order["amount"]
    return n, round(total, 2)


class TestPythonIsReady(unittest.TestCase):
    def test_python_version(self):
        self.assertGreaterEqual(
            sys.version_info[:2], (3, 9),
            "this course needs Python 3.9 or later, you are running %s: install a newer one from python.org/downloads"
            % sys.version.split()[0],
        )


class TestOrders(unittest.TestCase):
    def test_count_on_lesson_data(self):
        orders = committed_orders()
        n, _ = expected(orders)
        got = lesson.count_orders(orders)
        self.assertEqual(got, n, "count_orders gave %r but the file has %d orders: return len(orders)" % (got, n))

    def test_total_on_lesson_data(self):
        orders = committed_orders()
        _, total = expected(orders)
        got = lesson.total_amount(orders)
        self.assertAlmostEqual(got, total, delta=0.01, msg="total_amount gave %r but the amounts add up to %.2f: did the loop add every order?" % (got, total))

    def test_second_dataset(self):
        orders = built_orders(SECOND_SEED)
        n, total = expected(orders)
        self.assertEqual(lesson.count_orders(orders), n, "count_orders is wrong on a second dataset of %d orders: did you type a fixed number?" % n)
        self.assertAlmostEqual(lesson.total_amount(orders), total, delta=0.01, msg="total_amount is wrong on a second dataset (expected %.2f): did you type a fixed number?" % total)

    def test_small_cases(self):
        self.assertEqual(lesson.count_orders([]), 0, "an empty list has 0 orders")
        self.assertEqual(lesson.total_amount([]), 0, "an empty list totals 0")
        free = [{"order_id": "1", "dish": "curd rice", "amount": 0.0}]
        self.assertEqual(lesson.count_orders(free), 1, "a free order (amount 0.00) is still an order and counts as 1")
        self.assertEqual(lesson.total_amount(free), 0, "a free order adds 0 to the total")
        two = [{"order_id": "1", "dish": "a", "amount": 100.25}, {"order_id": "2", "dish": "b", "amount": 50.5}]
        self.assertEqual(lesson.count_orders(two), 2, "two orders should count as 2")
        self.assertAlmostEqual(lesson.total_amount(two), 150.75, delta=0.001, msg="100.25 + 50.50 should total 150.75")

    def test_load_orders_reads_the_file(self):
        rows = lesson.load_orders()
        self.assertEqual(len(rows), len(committed_orders()), "load_orders should read every row of data/orders.csv")
        self.assertIsInstance(rows[0]["amount"], float, "load_orders should turn amount into a number")


if __name__ == "__main__":
    unittest.main()
