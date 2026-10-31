"""Tests for lesson 05: lookups and SUMIFS like Excel.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

Expected answers are computed here in plain Python (dictionaries and loops, not the
lesson's functions), on the committed CSV files and on a second dataset that
make_data.build() makes in memory. Small hand-made cases cover the empty table, the
tie at a band boundary, the blank key and the zero amount.

Optional export check: if you rebuild the fixed region totals in Excel or Google Sheets
and save them as my_region_totals.csv (columns region,revenue) in this folder, the test
checks your numbers too. Without the file that test is skipped.
"""
import csv
import importlib.util
import os
import unittest

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
OTHER_SEED = 2031
REGIONS = ["North", "South", "East", "West"]
EXPORT = os.path.join(HERE, "my_region_totals.csv")


def read(name):
    with open(os.path.join(HERE, "data", name), newline="") as f:
        return list(csv.DictReader(f, quoting=csv.QUOTE_NONNUMERIC))


def ref_clean(v):
    """Independent version of the key fix: strip spaces, digits become a whole number."""
    if v is None:
        return None
    if isinstance(v, float):
        return int(v) if v == int(v) else v
    if isinstance(v, int):
        return v
    s = v.strip()
    while "  " in s:
        s = s.replace("  ", " ")
    if not s:
        return None
    return int(s) if all(ch in "0123456789" for ch in s) else s


def ref_expected(orders, customers):
    """Expected totals from dictionaries: the old sheet (exact and approximate) and the fixed one."""
    finance = sum(o["amount"] for o in orders)

    first_region = {}                       # exact match on the raw key: the first row wins
    for c in customers:
        first_region.setdefault(("n", float(c["customer_id"])), c["region"])
    old_exact = dict.fromkeys(REGIONS, 0.0)
    for o in orders:
        k = o["customer_id"]
        tag = ("n", float(k)) if isinstance(k, float) else ("t", k)
        if tag in first_region:
            old_exact[first_region[tag]] += o["amount"]

    ids = sorted(float(c["customer_id"]) for c in customers)
    last_region = {}                        # approximate match: the last row with key <= lookup
    for c in customers:
        last_region[float(c["customer_id"])] = c["region"]
    old_approx = dict.fromkeys(REGIONS, 0.0)
    for o in orders:
        k = o["customer_id"]
        if not isinstance(k, float):
            continue                        # text never matches a number column
        below = [i for i in ids if i <= k]
        if below:
            old_approx[last_region[max(below)]] += o["amount"]

    counts, region_of = {}, {}
    for c in customers:
        key = ref_clean(c["customer_id"])
        counts[key] = counts.get(key, 0) + 1
        region_of.setdefault(key, c["region"])
    fixed = dict.fromkeys(REGIONS + ["Ambiguous", "Unmatched"], 0.0)
    for o in orders:
        key = ref_clean(o["customer_id"])
        if counts.get(key, 0) > 1:
            fixed["Ambiguous"] += o["amount"]
        elif key in region_of:
            fixed[region_of[key]] += o["amount"]
        else:
            fixed["Unmatched"] += o["amount"]
    dups = sorted(k for k, n in counts.items() if n > 1)
    return finance, old_exact, old_approx, fixed, dups


class TestVlookup(unittest.TestCase):
    table = [[1001, "Alder Cafe", "North"], [1002, "Birch Deli", "South"], [1002, "Birch Deli", "East"],
             [1004, "Cedar Bakery", "West"]]

    def test_exact_match_returns_the_first_match(self):
        self.assertEqual(lesson.vlookup(1001, self.table, 3), "North")
        self.assertEqual(lesson.vlookup(1002, self.table, 3), "South",
                         "with a duplicate key, exact match stops at the FIRST matching row")
        self.assertEqual(lesson.vlookup(1001.0, self.table, 2), "Alder Cafe", "1001.0 and 1001 are the same number")

    def test_exact_match_misses_return_na(self):
        self.assertEqual(lesson.vlookup(1003, self.table, 3), lesson.NA, "a missing key gives #N/A, not a neighbour")
        self.assertEqual(lesson.vlookup("1001", self.table, 3), lesson.NA, "text '1001' never equals the number 1001")
        self.assertEqual(lesson.vlookup("1001 ", self.table, 3), lesson.NA)
        self.assertEqual(lesson.vlookup(None, self.table, 3), lesson.NA, "a blank key matches nothing")
        self.assertEqual(lesson.vlookup(1001, [], 3), lesson.NA, "an empty table matches nothing")

    def test_column_outside_the_table(self):
        for bad in (0, 4):
            with self.assertRaises(ValueError, msg="col_index %d is outside a 3 column table (#REF!)" % bad):
                lesson.vlookup(1001, self.table, bad)

    def test_approximate_match_on_bands(self):
        bands = [[0, 0.0], [10, 0.05], [25, 0.10], [50, 0.15]]   # quantity -> volume discount
        cases = {0: 0.0, 9: 0.0, 10: 0.05, 24.9: 0.05, 25: 0.10, 49: 0.10, 50: 0.15, 400: 0.15}
        for qty, want in cases.items():
            self.assertEqual(lesson.vlookup(qty, bands, 2, exact=False), want,
                             "approximate match: the largest band start <= %r" % qty)
        self.assertEqual(lesson.vlookup(-1, bands, 2, exact=False), lesson.NA, "below the first band: #N/A")
        self.assertEqual(lesson.vlookup("10", bands, 2, exact=False), lesson.NA, "text does not compare with numbers")

    def test_approximate_match_does_not_say_missing(self):
        self.assertEqual(lesson.vlookup(1003, self.table, 3, exact=False), "East",
                         "approximate match returns the row for 1002 (the last of the two) instead of #N/A")
        self.assertEqual(lesson.vlookup(9999, self.table, 3, exact=False), "West")


class TestXlookupAndKeys(unittest.TestCase):
    def test_xlookup(self):
        ids, regions = [5, 7, 7], ["North", "South", "East"]
        self.assertEqual(lesson.xlookup(7, ids, regions), "South", "first to last: the first 7 wins")
        self.assertEqual(lesson.xlookup(6, ids, regions), lesson.NA)
        self.assertEqual(lesson.xlookup(6, ids, regions, "Unmatched"), "Unmatched", "if_not_found replaces #N/A")
        self.assertEqual(lesson.xlookup("5", ids, regions, "none"), "none")
        self.assertEqual(lesson.xlookup(5, [], [], "none"), "none")
        with self.assertRaises(ValueError):
            lesson.xlookup(5, [5, 7], ["North"])

    def test_normalize_key(self):
        cases = [(1042.0, 1042), (1042, 1042), ("1042", 1042), ("1042 ", 1042), ("  1042", 1042),
                 ("C-7 ", "C-7"), ("Alder  Cafe", "Alder Cafe"), ("", None), ("   ", None), (None, None), (0.0, 0)]
        for raw, want in cases:
            got = lesson.normalize_key(raw)
            self.assertEqual((got, type(got)), (want, type(want)), "normalize_key(%r) should be %r" % (raw, want))


class TestSumifs(unittest.TestCase):
    amount = [100.0, 50.0, "n/a", 25.0, 0.0, None, 10.0]
    region = ["North", "South", "North", "North", "North", "North", "West"]
    qty = [12, 3, 40, 10, 99, 5, 1]

    def test_one_and_many_criteria(self):
        self.assertEqual(lesson.sumifs(self.amount, self.region, "North"), 125.0,
                         "text and empty cells in sum_range are skipped, and a zero adds nothing")
        self.assertEqual(lesson.sumifs(self.amount, self.region, "North", self.qty, ">=10"), 125.0)
        self.assertEqual(lesson.sumifs(self.amount, self.region, "North", self.qty, ">10"), 100.0,
                         "every criterion must hold (AND), and >10 excludes 10 itself")
        self.assertEqual(lesson.sumifs(self.amount, self.region, "<>North"), 60.0)
        self.assertEqual(lesson.sumifs(self.amount, self.qty, "<5"), 60.0)
        self.assertEqual(lesson.sumifs(self.amount, self.qty, 12), 100.0)

    def test_no_match_and_empty(self):
        self.assertEqual(lesson.sumifs(self.amount, self.region, "East"), 0)
        self.assertEqual(lesson.sumifs(self.amount, self.region, "North "), 0,
                         "'North ' with a trailing space is a different text from 'North'")
        self.assertEqual(lesson.sumifs([], [], "North"), 0)

    def test_ranges_must_line_up(self):
        with self.assertRaises(ValueError):
            lesson.sumifs(self.amount, self.region[:3], "North")


class DataChecks:
    orders = customers = None

    @classmethod
    def setUpClass(cls):
        cls.finance, cls.old_exact, cls.old_approx, cls.fixed, cls.dups = ref_expected(cls.orders, cls.customers)

    def test_finance_total(self):
        self.assertAlmostEqual(lesson.finance_total(self.orders), self.finance, places=2)

    def test_old_sheet_drops_unmatched_orders(self):
        got = lesson.naive_region_totals(self.orders, self.customers)
        self.assertEqual(sorted(got), sorted(REGIONS))
        for r in REGIONS:
            self.assertAlmostEqual(got[r], self.old_exact[r], places=2,
                                   msg="old sheet, %s: VLOOKUP the raw key with exact match, first row wins" % r)
        self.assertLess(sum(got.values()), self.finance - 1, "the old sheet must come out short of finance")

    def test_old_sheet_with_approximate_match(self):
        got = lesson.naive_region_totals(self.orders, self.customers, exact=False)
        for r in REGIONS:
            self.assertAlmostEqual(got[r], self.old_approx[r], places=2,
                                   msg="approximate match, %s: the last row with a key <= the order's key" % r)

    def test_duplicate_keys(self):
        self.assertEqual(lesson.duplicate_keys(self.customers), self.dups)

    def test_fixed_sheet_matches_finance(self):
        got = lesson.region_totals(self.orders, self.customers)
        self.assertEqual(sorted(got), sorted(self.fixed), "one bucket per region, plus Ambiguous and Unmatched")
        for r, want in self.fixed.items():
            self.assertAlmostEqual(got[r], want, places=2, msg="fixed sheet, %s: clean the key first" % r)
        self.assertAlmostEqual(sum(got.values()), self.finance, places=2,
                               msg="the fixed buckets must add up to the finance total")


class TestCommittedData(DataChecks, unittest.TestCase):
    orders, customers = read("orders.csv"), read("customers.csv")

    def test_committed_file_has_every_kind_of_mess(self):
        self.assertTrue(any(isinstance(o["customer_id"], str) and o["customer_id"].endswith(" ") for o in self.orders))
        self.assertEqual(len(self.dups), 1)


class TestSecondDataset(DataChecks, unittest.TestCase):
    """Another seed, built in memory: other customers, other amounts, another duplicate."""
    _data = make_data.build(OTHER_SEED)
    orders, customers = _data["orders"], _data["customers"]


class TestSmallTables(unittest.TestCase):
    customers = [{"customer_id": 1.0, "customer_name": "A", "region": "North"},
                 {"customer_id": 2.0, "customer_name": "B", "region": "South"},
                 {"customer_id": 2.0, "customer_name": "B", "region": "West"}]

    def test_empty_orders(self):
        self.assertEqual(lesson.region_totals([], self.customers),
                         dict.fromkeys(REGIONS + ["Ambiguous", "Unmatched"], 0))
        self.assertEqual(lesson.finance_total([]), 0)

    def test_every_bucket(self):
        orders = [{"customer_id": "1 ", "amount": 10.0}, {"customer_id": 2.0, "amount": 5.0},
                  {"customer_id": 3.0, "amount": 7.5}, {"customer_id": "", "amount": 2.0},
                  {"customer_id": 1.0, "amount": 0.0}]
        got = lesson.region_totals(orders, self.customers)
        self.assertEqual(got, {"North": 10.0, "South": 0, "East": 0, "West": 0, "Ambiguous": 5.0, "Unmatched": 9.5},
                         "'1 ' is customer 1, customer 2 is listed twice, 3 and a blank id are unmatched")
        self.assertEqual(lesson.naive_region_totals(orders, self.customers),
                         {"North": 0.0, "South": 5.0, "East": 0, "West": 0},
                         "the old sheet misses '1 ', drops 3 and the blank, and gives customer 2 to its first row")


@unittest.skipUnless(os.path.exists(EXPORT), "optional: no my_region_totals.csv exported from a spreadsheet")
class TestSpreadsheetExport(unittest.TestCase):
    def test_export_matches(self):
        with open(EXPORT, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        got = {r["region"].strip(): float(r["revenue"].replace(",", "")) for r in rows}
        _, _, _, want, _ = ref_expected(read("orders.csv"), read("customers.csv"))
        want = {k: v for k, v in want.items() if v}
        self.assertEqual(sorted(got), sorted(want), "your export should have one row per bucket: %s" % sorted(want))
        for k, v in want.items():
            self.assertAlmostEqual(got[k], v, places=2, msg="%s in your spreadsheet export" % k)


if __name__ == "__main__":
    unittest.main()
