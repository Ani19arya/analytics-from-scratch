"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py.

The expected answers come from make_data.expected(), which reads the generator's own
records of which rows it broke and how. Nothing is read from the solution file.
"""
import csv
import importlib.util
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_data  # noqa: E402

TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)

OTHER_SEED = 2027


def raw_rows():
    with open(os.path.join(HERE, "data", "orders_raw.csv"), newline="") as f:
        return list(csv.DictReader(f))


def row(order_id, order_date, amount, customer="Asha Rao", city="Pune"):
    return {"order_id": order_id, "order_date": order_date, "customer": customer, "city": city, "amount": amount}


class TestParsers(unittest.TestCase):
    def test_parse_date_formats(self):
        for s in ["2026-09-14", "14/09/2026", "Sep 14, 2026", "14-Sep-2026"]:
            self.assertEqual(lesson.parse_date(s), "2026-09-14", "%r should parse to 2026-09-14" % s)
        self.assertEqual(lesson.parse_date("03/04/2026"), "2026-04-03", "slash dates are day first in this file")
        self.assertIsNone(lesson.parse_date("TBD"))
        self.assertIsNone(lesson.parse_date(""))

    def test_parse_amount(self):
        self.assertEqual(lesson.parse_amount("$1,200.50"), (1200.5, "USD"))
        self.assertEqual(lesson.parse_amount("USD 75"), (75.0, "USD"))
        self.assertEqual(lesson.parse_amount(" INR 45,000 "), (45000.0, "INR"))
        self.assertEqual(lesson.parse_amount("INR 1,20,000"), (120000.0, "INR"))
        self.assertEqual(lesson.parse_amount("Rs 999"), (999.0, "INR"))
        self.assertEqual(lesson.parse_amount("Rs.250"), (250.0, "INR"))
        self.assertEqual(lesson.parse_amount("$0.00"), (0.0, "USD"), "zero is a real amount, keep it")
        self.assertIsNone(lesson.parse_amount("about 50"))
        self.assertIsNone(lesson.parse_amount("12 apples"))

    def test_parse_amount_rejects_numbers_without_digits(self):
        for s in ["$,", "INR ,,,", "$", "USD .", "$12,", "$,5"]:
            try:
                got = lesson.parse_amount(s)
            except ValueError as e:
                self.fail("parse_amount(%r) crashed with %r. The number must start with a digit, so the pattern "
                          "should not match and the function should return None." % (s, e))
            self.assertIsNone(got, "parse_amount(%r) should return None, not %r" % (s, got))

    def test_parse_amount_negative_is_not_a_sale(self):
        self.assertIsNone(lesson.parse_amount("-$50.00"), "a minus sign is not in the pattern, so a refund is rejected")


class TestCleanRowsSmall(unittest.TestCase):
    def test_empty_file(self):
        clean, report = lesson.clean_rows([])
        self.assertEqual(clean, [])
        self.assertEqual((report["rows_in"], report["rows_out"], report["dropped"]), (0, 0, {}))

    def test_duplicate_after_normalising(self):
        rows = [row("1", "2026-09-04", "$10"), row("1", "04/09/2026", " $10 ", customer="Asha  Rao ")]
        clean, report = lesson.clean_rows(rows)
        self.assertEqual(len(clean), 1, "the two rows are the same order once cleaned, so keep the first only")
        self.assertEqual(report["dropped"], {"duplicate": 1})

    def test_conflict_keeps_neither(self):
        rows = [row("7", "2026-09-04", "$10"), row("8", "2026-09-05", "$20"), row("7", "2026-09-04", "$11")]
        clean, report = lesson.clean_rows(rows)
        self.assertEqual([r["order_id"] for r in clean], ["8"],
                         "order 7 has two different amounts: drop both rows as conflict, do not pick one")
        self.assertEqual(report["dropped"], {"conflict": 2})
        self.assertEqual(sorted(report["dropped_rows"]), [("7", "conflict"), ("7", "conflict")])

    def test_missing_cell_and_zero(self):
        short = {"order_id": "9", "order_date": "2026-09-06", "customer": "Ben Ortiz", "city": None, "amount": "$0"}
        clean, report = lesson.clean_rows([short, row("10", "", "$5"), row("11", "2026-09-06", "$,")])
        self.assertEqual(clean, [{"order_id": "9", "order_date": "2026-09-06", "customer": "Ben Ortiz",
                                  "city": "Unknown", "amount": 0.0, "currency": "USD"}],
                         "a missing city (None) is filled with Unknown, and a $0 order is kept")
        self.assertEqual(report["dropped"], {"blank_date": 1, "bad_amount": 1})


class TestOnLessonData(unittest.TestCase):
    def check(self, raw, want):
        clean, report = lesson.clean_rows(raw)
        self.assertEqual(report["rows_in"], want["rows_in"])
        self.assertEqual(report["dropped"], want["dropped"],
                         "drop counts by reason differ; check the order blank_date, bad_date, blank_amount, "
                         "bad_amount, duplicate, conflict")
        self.assertEqual(report["rows_out"], len(want["clean"]))
        self.assertEqual(len(report["dropped_rows"]), sum(want["dropped"].values()))
        self.assertEqual(clean, want["clean"], "the clean rows differ from the generator's record of the true orders")
        expected_trim = sum(1 for r in raw for v in r.values() if (v or "") != " ".join((v or "").split()))
        self.assertEqual(report["trimmed_cells"], expected_trim)
        self.assertEqual(report["filled_city"], sum(1 for r in want["clean"] if r["city"] == "Unknown"))

    def test_committed_file(self):
        raw = raw_rows()
        self.assertEqual(len(raw), 107)
        self.check(raw, make_data.expected(make_data.DEFAULT_SEED))

    def test_second_dataset(self):
        """Another seed, built in memory. A cleaner tuned to the committed file fails here."""
        self.check(make_data.build(OTHER_SEED)["orders_raw"], make_data.expected(OTHER_SEED))

    def test_clean_rows_are_clean(self):
        clean, _ = lesson.clean_rows(raw_rows())
        ids = [r["order_id"] for r in clean]
        self.assertEqual(len(ids), len(set(ids)), "a duplicate order survived")
        for r in clean:
            self.assertRegex(r["order_date"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertIsInstance(r["amount"], float)
            self.assertIn(r["currency"], ("USD", "INR"))
            self.assertEqual(r["customer"], " ".join(r["customer"].split()))
            self.assertNotEqual(r["city"], "")


if __name__ == "__main__":
    unittest.main()
