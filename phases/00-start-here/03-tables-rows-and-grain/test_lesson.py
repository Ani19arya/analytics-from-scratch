"""Tests for lesson 00-03: tables, rows and grain.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

The expected answers are worked out here in plain Python, never copied from the
solution. The functions also run on a second dataset with different repeats.
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

SECOND_SEED = 5
TABLES = ["customers", "orders", "order_items"]


def committed():
    out = {}
    for t in TABLES:
        with open(os.path.join(HERE, "data", t + ".csv"), newline="") as f:
            out[t] = list(csv.DictReader(f))
    return out


def ref_dups(rows, key):
    seen, out = [], {}
    for r in rows:
        k = tuple(r[c] for c in key)
        if k in seen:
            out[k] = out.get(k, 1) + 1
        else:
            seen.append(k)
    return out


def ref_fees(orders):
    first = {}
    for r in orders:
        first.setdefault(r["order_id"], float(r["delivery_fee"]))
    return round(sum(first.values()), 2)


class TestGrainAndKeys(unittest.TestCase):
    def test_grain(self):
        expected = {"customers": "one row per customer", "orders": "one row per order", "order_items": "one row per order line"}
        for table, grain in expected.items():
            got = lesson.GRAIN.get(table, "").strip().lower()
            self.assertEqual(got, grain, "GRAIN[%r]: ask what one row of %s.csv describes" % (table, table))

    def test_keys_are_columns_and_minimal(self):
        data = make_data.build(SECOND_SEED)
        for table in TABLES:
            key = list(lesson.KEYS.get(table, []))
            self.assertTrue(key, "KEYS[%r] is empty: list the column(s) that identify one row" % table)
            for col in key:
                self.assertIn(col, data[table][0], "%r is not a column of %s" % (col, table))
            rows = data[table]
            if table == "orders":
                rows = list({r["order_id"]: r for r in rows}.values())
            self.assertEqual(ref_dups(rows, key), {}, "KEYS[%r] = %r does not identify one row: some values repeat" % (table, key))
            for col in key:
                smaller = [c for c in key if c != col]
                if smaller:
                    self.assertNotEqual(ref_dups(rows, smaller), {}, "KEYS[%r] has a column you do not need: %r" % (table, col))

    def test_keys_match_the_grain(self):
        self.assertEqual(list(lesson.KEYS.get("customers", [])), ["customer_id"], "a customer is identified by customer_id, not by name: two customers can share a name")
        self.assertEqual(list(lesson.KEYS.get("orders", [])), ["order_id"], "an order is identified by order_id")
        self.assertEqual(sorted(lesson.KEYS.get("order_items", [])), ["line_no", "order_id"], "an order line needs order_id AND line_no: line 1 exists in every order")


class TestSmallCases(unittest.TestCase):
    def test_duplicate_keys(self):
        self.assertEqual(lesson.duplicate_keys([], ["id"]), {}, "no rows means no repeats")
        rows = [{"id": "1", "x": "a"}, {"id": "2", "x": "a"}, {"id": "1", "x": "b"}, {"id": "1", "x": "a"}]
        self.assertEqual(lesson.duplicate_keys(rows, ["id"]), {("1",): 3}, "id 1 appears 3 times; id 2 once, so it is not listed")
        self.assertEqual(lesson.duplicate_keys(rows, ["id", "x"]), {("1", "a"): 2}, "with two key columns, only the pair (1, a) repeats")

    def test_is_primary_key(self):
        self.assertTrue(lesson.is_primary_key([{"id": "1"}, {"id": "2"}], ["id"]), "unique, non-blank values make a key")
        self.assertFalse(lesson.is_primary_key([{"id": "1"}, {"id": "1"}], ["id"]), "a repeated value cannot be a key")
        self.assertFalse(lesson.is_primary_key([{"id": "1"}, {"id": ""}], ["id"]), "a blank value cannot be a key")
        self.assertTrue(lesson.is_primary_key([], ["id"]), "an empty table breaks no rule")

    def test_relationship(self):
        one = [{"k": "1"}, {"k": "2"}]
        many = [{"k": "1"}, {"k": "1"}, {"k": "2"}]
        self.assertEqual(lesson.relationship(one, one, "k"), "one-to-one", "both sides unique")
        self.assertEqual(lesson.relationship(one, many, "k"), "one-to-many", "left unique, right repeats")
        self.assertEqual(lesson.relationship(many, one, "k"), "many-to-one", "left repeats, right unique")
        self.assertEqual(lesson.relationship(many, many, "k"), "many-to-many", "both sides repeat")

    def test_total_delivery_fees(self):
        self.assertEqual(lesson.total_delivery_fees([]), 0, "no orders, no fees")
        rows = [{"order_id": "1", "delivery_fee": "25.00"}, {"order_id": "2", "delivery_fee": "0.00"}, {"order_id": "1", "delivery_fee": "25.00"}]
        self.assertEqual(lesson.total_delivery_fees(rows), 25.0, "order 1 is repeated, so its fee counts once: 25 + 0 = 25.0")


class TestOnData(unittest.TestCase):
    def check(self, data, label):
        orders = data["orders"]
        exp = ref_dups(orders, ["order_id"])
        self.assertEqual(lesson.duplicate_keys(orders, ["order_id"]), exp, "%s: the repeated order_ids should be %r" % (label, exp))
        self.assertFalse(lesson.is_primary_key(orders, ["order_id"]), "%s: order_id repeats in orders.csv, so it is not unique yet" % label)
        self.assertTrue(lesson.is_primary_key(data["customers"], ["customer_id"]), "%s: customer_id is unique in customers" % label)
        self.assertTrue(lesson.is_primary_key(data["order_items"], ["order_id", "line_no"]), "%s: (order_id, line_no) is unique in order_items" % label)
        self.assertEqual(lesson.relationship(data["customers"], orders, "customer_id"), "one-to-many", "%s: one customer, many orders" % label)
        self.assertEqual(lesson.relationship(orders, data["order_items"], "order_id"), "many-to-many",
                         "%s: with repeated orders, orders to items looks many-to-many: a warning sign" % label)
        fees = ref_fees(orders)
        got = lesson.total_delivery_fees(orders)
        self.assertAlmostEqual(got, fees, delta=0.001, msg="%s: delivery fees should be %.2f, got %r: count each order once" % (label, fees, got))

    def test_lesson_data(self):
        self.check(committed(), "lesson data")

    def test_second_dataset(self):
        self.check(make_data.build(SECOND_SEED), "second dataset")


if __name__ == "__main__":
    unittest.main()
