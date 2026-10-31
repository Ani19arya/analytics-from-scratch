"""Tests for lesson 00-06: Python for spreadsheet people.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

The expected answers are worked out here a second way (a regular expression
instead of float() inside try), never copied from the solution. The functions
also run on a second dataset with different messy cells.
"""
import csv
import importlib.util
import os
import re
import sys
import tempfile
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

SECOND_SEED = 11
NUMBER = re.compile(r"^-?\d+(\.\d+)?$")


def ref_number(text):
    t = re.sub(r"^\s*[Rr][Ss]\s*", "", text).strip().replace(",", "")
    return float(t) if NUMBER.match(t) else None


def ref_numbers(rows, column, keep=lambda r: True):
    return [ref_number(r[column]) for r in rows if keep(r) and ref_number(r[column]) is not None]


def committed():
    with open(os.path.join(HERE, "data", "purchases.csv"), newline="") as f:
        return list(csv.DictReader(f))


def call(name, *args):
    try:
        return getattr(lesson, name)(*args)
    except ValueError as err:
        raise AssertionError("%s crashed with ValueError: %s. Finish to_number so it returns None for cells that are not numbers" % (name, err))


class TestToNumber(unittest.TestCase):
    def test_clean_and_messy_cells(self):
        cases = {"141.94": 141.94, "1,250.00": 1250.0, " 300 ": 300.0, "Rs 450": 450.0, "rs450": 450.0,
                 "-120.00": -120.0, "0": 0.0, "0.00": 0.0, "12,34,567.5": 1234567.5}
        for text, value in cases.items():
            got = call("to_number", text)
            self.assertEqual(got, value, "to_number(%r) should be %r, got %r" % (text, value, got))

    def test_cells_that_are_not_numbers(self):
        for text in ["", "   ", "n/a", "N/A", "-", "92O", "abc", "Rs", "Rs ,"]:
            got = call("to_number", text)
            self.assertIsNone(got, "to_number(%r) should be None (no number in it), got %r" % (text, got))


class TestSmallCases(unittest.TestCase):
    rows = [
        {"category": "vegetables", "amount": "100.00"},
        {"category": "Vegetables ", "amount": "1,000.00"},
        {"category": "dairy", "amount": "0"},
        {"category": "dairy", "amount": ""},
        {"category": "VEGETABLES", "amount": "n/a"},
        {"category": "gas", "amount": "-50"},
    ]

    def test_empty_sheet(self):
        self.assertEqual(call("total", [], "amount"), 0, "an empty sheet totals 0")
        self.assertEqual(call("count_numbers", [], "amount"), 0, "an empty sheet has no numbers")
        self.assertEqual(call("sumif", [], "amount", "category", "dairy"), 0, "an empty sheet sums to 0")

    def test_total_count_sumif(self):
        self.assertEqual(call("total", self.rows, "amount"), 1050.0, "100 + 1000 + 0 - 50 = 1050.0: blanks and n/a add nothing")
        self.assertEqual(call("count_numbers", self.rows, "amount"), 4, "100, 1000, 0 and -50 are numbers; a blank and n/a are not")
        self.assertEqual(call("sumif", self.rows, "amount", "category", "vegetables"), 1100.0,
                         "vegetables, 'Vegetables ' and VEGETABLES are one category: 100 + 1000 = 1100.0")
        self.assertEqual(call("sumif", self.rows, "amount", "category", " Dairy"), 0, "dairy is 0 + blank = 0")
        self.assertEqual(call("sumif", self.rows, "amount", "category", "fish"), 0, "no matching rows sum to 0")


class TestOnData(unittest.TestCase):
    def check(self, rows, label):
        nums = ref_numbers(rows, "amount")
        got = call("total", rows, "amount")
        self.assertAlmostEqual(got, round(sum(nums), 2), delta=0.011,
                               msg="%s: total should be %.2f, got %r" % (label, sum(nums), got))
        self.assertEqual(call("count_numbers", rows, "amount"), len(nums), "%s: count_numbers should be %d" % (label, len(nums)))
        cats = sorted(set(r["category"].strip().lower() for r in rows))
        for cat in cats:
            exp = round(sum(ref_numbers(rows, "amount", lambda r: r["category"].strip().lower() == cat)), 2)
            got = call("sumif", rows, "amount", "category", cat)
            self.assertAlmostEqual(got, exp, delta=0.011, msg="%s: sumif for %r should be %.2f, got %r" % (label, cat, exp, got))
        bad = [(i, r["amount"]) for i, r in enumerate(rows, 2)
               if ref_number(r["amount"]) is None and r["amount"].strip().lower() not in ("", "n/a", "-")]
        self.assertEqual(call("bad_values", rows, "amount"), bad, "%s: the cells to check by hand should be %r" % (label, bad))

    def test_read_rows(self):
        rows = lesson.read_rows()
        self.assertEqual(rows, committed(), "read_rows() should return every row of data/purchases.csv as a dictionary")

    def test_lesson_data(self):
        self.check(lesson.read_rows() or committed(), "lesson data")

    def test_second_dataset(self):
        rows = make_data.build(SECOND_SEED)["purchases"]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "purchases.csv")
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            self.assertEqual(lesson.read_rows(path), rows, "read_rows(path) should read the file it is given, not always data/purchases.csv")
        self.check(rows, "second dataset")


if __name__ == "__main__":
    unittest.main()
