"""Tests for lesson 05: profile a table before you trust it.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

Expected profiles and reasons are computed here in plain Python, in a different way from
the lesson (float() instead of patterns), on the committed file and on a second file that
make_data.build(seed=2033) makes in memory. The duplicate counts are also checked against
make_data.expected(), the generator's own record. Small cases cover the empty table, the
all-null column, a tie between types, a zero, and the difference between "" and None.
"""
import csv
import importlib.util
import os
import unittest
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" \
    else os.path.join(HERE, "exercise.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lesson = load("lesson", TARGET)
make_data = load("make_data", os.path.join(HERE, "make_data.py"))
OTHER_SEED = 2033
REQUIRED = ["payment_id", "customer_id", "paid_at", "plan", "amount", "status"]
RULES = {"amount": (1.0, 1000.0), "paid_at": ("2026-07-01", "2026-09-30")}


def read_rows():
    with open(os.path.join(HERE, "data", "payments.csv"), newline="") as f:
        return list(csv.DictReader(f))


def ref_family(v):
    """None for a null, else number, date or text."""
    if v is None or not v.strip() or v.strip().lower() in ("null", "none", "n/a", "\\n"):
        return None
    s = v.strip()
    if len(s) == 10 and s[4] == s[7] == "-" and (s[:4] + s[5:7] + s[8:]).isdigit():
        try:
            date(int(s[:4]), int(s[5:7]), int(s[8:]))
            return "date"
        except ValueError:
            return "text"
    if all(ch in "-0123456789." for ch in s):
        try:
            float(s)
            return "number"
        except ValueError:
            return "text"
    return "text"


def ref_reasons(rows):
    keys = [r["payment_id"] for r in rows if ref_family(r["payment_id"])]
    reasons = []
    if len(keys) != len(set(keys)):
        reasons.append(("duplicate_keys", "payment_id", len(keys) - len(set(keys))))
    for col in rows[0]:
        fams = [ref_family(r[col]) for r in rows]
        nulls = fams.count(None)
        counts = {f: fams.count(f) for f in ("number", "date", "text") if fams.count(f)}
        if col in REQUIRED and nulls:
            reasons.append(("missing", col, nulls))
        if len(counts) > 1:
            reasons.append(("mixed_types", col, sum(counts.values()) - max(counts.values())))
        if col in RULES:
            low, high = RULES[col]
            fam = "number" if isinstance(low, float) else "date"
            vals = [float(r[col]) if fam == "number" else r[col].strip() for r, f in zip(rows, fams) if f == fam]
            bad = sum(1 for x in vals if x < low or x > high)
            if bad:
                reasons.append(("out_of_range", col, bad))
    return reasons


def ref_revenue(rows):
    total, extra, seen = 0.0, 0.0, set()
    for r in rows:
        paid = r["status"] == "paid" and ref_family(r["amount"]) == "number"
        if paid:
            total += float(r["amount"])
            if r["payment_id"] in seen:
                extra += float(r["amount"])
        seen.add(r["payment_id"])
    return round(total, 2), round(extra, 2)


class TestClassify(unittest.TestCase):
    def test_nulls_three_ways(self):
        for v in ("", "   ", None):
            self.assertEqual(lesson.classify(v), "empty", "%r is an empty cell" % (v,))
        for v in ("NULL", "null", " N/A ", "None", "\\N"):
            self.assertEqual(lesson.classify(v), "null_text", "%r is text that means no value" % v)

    def test_values(self):
        cases = {"42": "int", "0": "int", "-49.00": "float", "149,00": "text", "2026-09-30": "date",
                 "2026-02-30": "text", "NA": "text", "PAY-00001": "text", "1e5": "text"}
        for v, want in cases.items():
            self.assertEqual(lesson.classify(v), want, "classify(%r) should be %r" % (v, want))


class TestProfileColumn(unittest.TestCase):
    def test_empty_column(self):
        p = lesson.profile_column([])
        self.assertEqual((p["count"], p["nulls"], p["null_pct"], p["distinct"], p["main_type"], p["min"], p["max"]),
                         (0, 0, 0.0, 0, None, None, None), "no rows: zeros and Nones, and no division by zero")

    def test_all_null_column(self):
        p = lesson.profile_column(["", None, "NULL", " "])
        self.assertEqual((p["empty"], p["null_text"], p["nulls"], p["null_pct"]), (3, 1, 4, 100.0))
        self.assertEqual((p["types"], p["main_type"], p["mixed"], p["distinct"]), ({}, None, False, 0))

    def test_numbers_text_and_zero(self):
        p = lesson.profile_column(["10.00", "0", "", "149,00", "-3", "10.00"])
        self.assertEqual(p["types"], {"number": 4, "text": 1})
        self.assertEqual((p["main_type"], p["mixed"], p["min"], p["max"]), ("number", True, -3.0, 10.0),
                         "min and max come from the main type only, as numbers, and 0 is a value, not a null")
        self.assertEqual(p["distinct"], 4)
        self.assertEqual(p["null_pct"], 16.7)

    def test_tie_breaks_number_then_date_then_text(self):
        self.assertEqual(lesson.profile_column(["1", "x"])["main_type"], "number")
        self.assertEqual(lesson.profile_column(["x", "2026-01-01"])["main_type"], "date")

    def test_case_variants_are_distinct(self):
        self.assertEqual(lesson.profile_column(["Pro", "pro", "PRO", "Pro"])["distinct"], 3,
                         "distinct compares values exactly as written, which is how it exposes case variants")


class TestProfileTable(unittest.TestCase):
    def test_empty_table(self):
        p = lesson.profile_table([], "id")
        self.assertEqual((p["rows"], p["columns"], p["duplicate_key_rows"], p["exact_duplicate_rows"]), (0, {}, 0, 0))

    def test_keys(self):
        rows = [{"id": "1", "v": "5"}, {"id": "1", "v": "5"}, {"id": "1", "v": "6"}, {"id": "", "v": "7"},
                {"id": "NULL", "v": "8"}, {"id": "2", "v": "0"}]
        p = lesson.profile_table(rows, "id")
        self.assertEqual((p["null_keys"], p["distinct_keys"], p["duplicate_keys"], p["duplicate_key_rows"],
                          p["exact_duplicate_rows"]), (2, 2, ["1"], 2, 1),
                         "two null keys, keys 1 and 2, key 1 has two extra rows, one of them an exact copy")


class TestRangeAndFitness(unittest.TestCase):
    def test_out_of_range(self):
        self.assertEqual(lesson.out_of_range(["1", "1000", "1000.01", "0.99", "-5", "", "x", "4900.00"], 1.0, 1000.0), 4,
                         "the ends are inside the range; blanks and text are not counted here")
        self.assertEqual(lesson.out_of_range(["2026-07-01", "2026-09-30", "2026-10-01", "2025-07-14", "TBD"],
                                             "2026-07-01", "2026-09-30"), 2)

    def test_clean_table_is_fit(self):
        rows = [{"payment_id": "P1", "customer_id": "C1", "paid_at": "2026-08-01", "plan": "Pro", "amount": "49.00",
                 "country": "NA", "status": "paid"}]
        fit, reasons, _ = lesson.check_fitness(rows, "payment_id", REQUIRED, RULES)
        self.assertEqual((fit, reasons), (True, []), "a clean row is fit, and country NA (Namibia) is not a null")

    def test_no_rows_is_not_fit(self):
        fit, reasons, _ = lesson.check_fitness([], "payment_id", REQUIRED, RULES)
        self.assertEqual((fit, reasons), (False, [("no_rows", None, 0)]), "an empty table is never fit for a board number")


class DataChecks:
    rows = seed = None

    def test_reasons(self):
        fit, reasons, profile = lesson.check_fitness(self.rows, "payment_id", REQUIRED, RULES)
        self.assertFalse(fit)
        self.assertEqual(reasons, ref_reasons(self.rows),
                         "reasons differ: check the order (duplicate keys first, then each column: missing, "
                         "mixed_types, out_of_range) and that '', spaces, NULL and N/A all count as missing")

    def test_duplicates_match_the_generator(self):
        p = lesson.profile_table(self.rows, "payment_id")
        want = make_data.expected(self.seed)
        self.assertEqual((p["rows"], p["duplicate_key_rows"], p["exact_duplicate_rows"]),
                         (want["rows"], want["duplicate_key_rows"], want["exact_duplicate_rows"]))

    def test_revenue_and_inflation(self):
        total, extra = ref_revenue(self.rows)
        self.assertAlmostEqual(lesson.naive_revenue(self.rows), total, places=2,
                               msg="naive revenue: paid rows whose amount reads as a number")
        self.assertAlmostEqual(lesson.duplicate_inflation(self.rows), extra, places=2,
                               msg="inflation: paid amounts on rows after the first for their key")
        self.assertGreater(extra, 0)

    def test_column_profiles(self):
        p = lesson.profile_table(self.rows, "payment_id")
        for col in self.rows[0]:
            fams = [ref_family(r[col]) for r in self.rows]
            got = p["columns"][col]
            self.assertEqual(got["nulls"], fams.count(None), "%s: nulls" % col)
            self.assertEqual(got["empty"], sum(1 for r in self.rows if not r[col].strip()), "%s: empty cells" % col)
            self.assertEqual(got["distinct"], len({r[col] for r, f in zip(self.rows, fams) if f}), "%s: distinct" % col)


class TestCommittedFile(DataChecks, unittest.TestCase):
    rows, seed = read_rows(), make_data.DEFAULT_SEED

    def test_is_none_finds_nothing(self):
        self.assertEqual(sum(1 for r in self.rows if r["amount"] is None), 0,
                         "csv gives '' for an empty cell, never None: that is why classify checks both")


class TestSecondFile(DataChecks, unittest.TestCase):
    rows, seed = make_data.build(OTHER_SEED)["payments"], OTHER_SEED


if __name__ == "__main__":
    unittest.main()
