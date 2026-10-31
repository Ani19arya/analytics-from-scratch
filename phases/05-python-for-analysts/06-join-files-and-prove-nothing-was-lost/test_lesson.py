"""Tests for lesson 06: join two files and prove nothing was lost.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

Expected numbers are computed here in plain Python by counting matches per line, never by
calling the lesson's join. They are checked on the committed files and on a second pair of
files that make_data.build(seed=2034) makes in memory. Small cases cover empty files, a blank
(NULL) key on both sides, a key listed twice, a column name on both sides and a zero amount.

If pandas is installed, one more test compares your numbers with pandas' merge(...,
indicator=True) and checks that merge(validate="many_to_one") refuses the raw catalogue.
Without pandas that test is skipped.
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
OTHER_SEED = 2034
try:
    import pandas as pd
    HAVE_PANDAS = True
except ImportError:
    HAVE_PANDAS = False


def read(name):
    with open(os.path.join(HERE, "data", name), newline="") as f:
        return list(csv.DictReader(f))


def ref_expected(lines, products):
    count, cats = {}, {}
    for p in products:
        if p["sku"].strip():
            count[p["sku"]] = count.get(p["sku"], 0) + 1
            cats.setdefault(p["sku"], set()).add(p["category"])
    left_total = sum(float(l["amount"]) for l in lines)
    joined_rows = joined_amount = fan_rows = fan_amount = 0
    unmatched_rows, unmatched_amount, unmatched_keys = 0, 0.0, set()
    buckets = {}
    for l in lines:
        sku, amt = l["sku"], float(l["amount"])
        n = count.get(sku, 0) if sku.strip() else 0
        joined_rows += max(n, 1)
        joined_amount += max(n, 1) * amt
        if n > 1:
            fan_rows += n - 1
            fan_amount += (n - 1) * amt
        if n == 0:
            unmatched_rows += 1
            unmatched_amount += amt
            if sku.strip():
                unmatched_keys.add(sku)
        if not sku.strip():
            b = "No SKU"
        elif sku not in cats:
            b = "Unmatched"
        elif len(cats[sku]) > 1:
            b = "Needs review"
        else:
            b = next(iter(cats[sku]))
        buckets[b] = buckets.get(b, 0.0) + amt
    used = {l["sku"] for l in lines}
    return {"left_rows": len(lines), "right_rows": len(products), "joined_rows": joined_rows,
            "left_amount": left_total, "joined_amount": joined_amount, "fanout_rows": fan_rows,
            "fanout_amount": fan_amount, "unmatched_left_rows": unmatched_rows,
            "unmatched_left_amount": unmatched_amount, "unmatched_left_keys": sorted(unmatched_keys),
            "unmatched_right_keys": sorted(k for k in count if k not in used),
            "duplicate_right_keys": sorted(k for k, n in count.items() if n > 1),
            "blank_key_rows": sum(1 for l in lines if not l["sku"].strip())}, buckets


LEFT = [{"id": "1", "sku": "A", "amount": "10.00"}, {"id": "2", "sku": "B", "amount": "5.00"},
        {"id": "3", "sku": "", "amount": "49.00"}, {"id": "4", "sku": "Z", "amount": "0.00"},
        {"id": "5", "sku": "A", "amount": "1.00"}]
RIGHT = [{"sku": "A", "category": "Rugs", "id": "r1"}, {"sku": "A", "category": "Decor", "id": "r2"},
         {"sku": "B", "category": "Sofas", "id": "r3"}, {"sku": "", "category": "Ghost", "id": "r4"},
         {"sku": "C", "category": "Tables", "id": "r5"}]


class TestJoins(unittest.TestCase):
    def test_left_join_fans_out_and_keeps_unmatched(self):
        got = lesson.left_join(LEFT, RIGHT, "sku")
        self.assertEqual([(r["id"], r["category"]) for r in got],
                         [("1", "Rugs"), ("1", "Decor"), ("2", "Sofas"), ("3", None), ("4", None), ("5", "Rugs"),
                          ("5", "Decor")],
                         "every left row in order; A matches twice (fan-out); a blank key never matches, "
                         "not even a blank key on the right")
        self.assertEqual(got[0]["id_right"], "r1", "a right column whose name is already on the left becomes id_right")
        self.assertIsNone(got[3]["id_right"])

    def test_inner_join(self):
        got = lesson.inner_join(LEFT, RIGHT, "sku")
        self.assertEqual([r["id"] for r in got], ["1", "1", "2", "5", "5"], "unmatched and blank keys drop out")

    def test_empty_inputs(self):
        self.assertEqual(lesson.left_join([], RIGHT, "sku"), [])
        self.assertEqual(lesson.left_join(LEFT, [], "sku"), LEFT, "nothing to add: the left rows come back as they were")
        self.assertEqual(lesson.inner_join(LEFT, [], "sku"), [])


class TestReconcile(unittest.TestCase):
    def test_small_report(self):
        joined = lesson.left_join(LEFT, RIGHT, "sku")
        rep = lesson.reconcile(LEFT, RIGHT, joined, "sku", "amount")
        want = {"left_rows": 5, "right_rows": 5, "joined_rows": 7, "row_diff": 2, "left_amount": 65.0,
                "joined_amount": 76.0, "amount_diff": 11.0, "blank_key_rows": 1, "unmatched_left_keys": ["Z"],
                "unmatched_left_rows": 2, "unmatched_left_amount": 49.0, "unmatched_right_keys": ["C"],
                "duplicate_right_keys": ["A"], "fanout_rows": 2, "fanout_amount": 11.0,
                "problems": ["rows_added", "amount_changed", "unmatched_left"], "ok": False}
        for k, v in want.items():
            self.assertEqual(rep[k], v, "reconcile()[%r] should be %r" % (k, v))

    def test_inner_join_loses_rows(self):
        joined = lesson.inner_join(LEFT, [{"sku": "A", "category": "Rugs"}], "sku")
        rep = lesson.reconcile(LEFT, [{"sku": "A", "category": "Rugs"}], joined, "sku", "amount")
        self.assertEqual((rep["row_diff"], rep["amount_diff"]), (-3, -54.0))
        self.assertEqual(rep["problems"], ["rows_lost", "amount_changed", "unmatched_left"])

    def test_clean_join_is_ok(self):
        right = [{"sku": "A", "category": "Rugs"}]
        left = [{"sku": "A", "amount": "3.50"}, {"sku": "A", "amount": "0"}]
        rep = lesson.reconcile(left, right, lesson.left_join(left, right, "sku"), "sku", "amount")
        self.assertEqual((rep["ok"], rep["problems"]), (True, []))
        empty = lesson.reconcile([], [], [], "sku", "amount")
        self.assertEqual((empty["ok"], empty["left_amount"], empty["joined_amount"]), (True, 0, 0))

    def test_assert_reconciled(self):
        rep = lesson.reconcile(LEFT, RIGHT, lesson.left_join(LEFT, RIGHT, "sku"), "sku", "amount")
        with self.assertRaises(ValueError, msg="a join that adds rows must stop the pipeline"):
            lesson.assert_reconciled(rep)
        with self.assertRaises(ValueError):
            lesson.assert_reconciled(rep, allow=("unmatched_left",))
        ok = lesson.reconcile(LEFT, [], LEFT, "sku", "amount")
        lesson.assert_reconciled(ok, allow=("unmatched_left",))


class TestFix(unittest.TestCase):
    def test_clean_catalogue(self):
        products = [{"sku": "B", "category": "Sofas"}, {"sku": "A", "category": "Rugs"}, {"sku": "A", "category": "Rugs"},
                    {"sku": "C", "category": "Decor"}, {"sku": "C", "category": "Lighting"}, {"sku": " ", "category": "X"}]
        self.assertEqual(lesson.clean_catalogue(products),
                         [{"sku": "A", "category": "Rugs"}, {"sku": "B", "category": "Sofas"},
                          {"sku": "C", "category": "Needs review"}],
                         "exact repeats collapse, a disagreement becomes Needs review, a blank sku is dropped")
        self.assertEqual(lesson.clean_catalogue([]), [])

    def test_revenue_by_category(self):
        joined = lesson.left_join(LEFT, lesson.clean_catalogue(RIGHT), "sku")
        self.assertEqual(lesson.revenue_by_category(joined),
                         {"Needs review": 11.0, "No SKU": 49.0, "Sofas": 5.0, "Unmatched": 0.0},
                         "every line in one bucket, a zero amount still makes its bucket appear")


class DataChecks:
    lines = products = None

    @classmethod
    def setUpClass(cls):
        cls.want, cls.buckets = ref_expected(cls.lines, cls.products)

    def test_naive_join_report(self):
        joined = lesson.left_join(self.lines, self.products, "sku")
        rep = lesson.reconcile(self.lines, self.products, joined, "sku", "amount")
        for k, v in self.want.items():
            if isinstance(v, float):
                self.assertAlmostEqual(rep[k], v, places=2, msg="%s on the raw catalogue" % k)
            else:
                self.assertEqual(rep[k], v, "%s on the raw catalogue" % k)
        self.assertIn("rows_added", rep["problems"], "the raw catalogue repeats skus, so the join must add rows")

    def test_fixed_join_keeps_the_totals(self):
        catalogue = lesson.clean_catalogue(self.products)
        joined = lesson.left_join(self.lines, catalogue, "sku")
        rep = lesson.reconcile(self.lines, catalogue, joined, "sku", "amount")
        self.assertEqual(rep["problems"], ["unmatched_left"],
                         "after clean_catalogue, rows and amount must match the order lines exactly")
        got = lesson.revenue_by_category(joined)
        self.assertEqual(sorted(got), sorted(self.buckets))
        for k, v in self.buckets.items():
            self.assertAlmostEqual(got[k], v, places=2, msg="revenue for %s" % k)
        self.assertAlmostEqual(sum(got.values()), self.want["left_amount"], places=2)

    @unittest.skipUnless(HAVE_PANDAS, "optional: pandas is not installed")
    def test_against_pandas(self):
        left, right = pd.DataFrame(self.lines), pd.DataFrame(self.products)
        left["amount"] = left["amount"].astype(float)
        left.loc[left["sku"] == "", "sku"] = None     # a blank sku is a missing key
        merged = left.merge(right, on="sku", how="left", indicator=True)
        rep = lesson.reconcile(self.lines, self.products, lesson.left_join(self.lines, self.products, "sku"),
                               "sku", "amount")
        self.assertEqual(len(merged), rep["joined_rows"])
        self.assertEqual(int((merged["_merge"] == "left_only").sum()), rep["unmatched_left_rows"])
        self.assertAlmostEqual(float(merged["amount"].sum()), rep["joined_amount"], places=2)
        with self.assertRaises(pd.errors.MergeError):
            left.merge(right, on="sku", how="left", validate="many_to_one")
        clean = pd.DataFrame(lesson.clean_catalogue(self.products))
        self.assertEqual(len(left.merge(clean, on="sku", how="left", validate="many_to_one")), len(left))


class TestCommittedFiles(DataChecks, unittest.TestCase):
    lines, products = read("order_lines.csv"), read("products.csv")


class TestSecondFiles(DataChecks, unittest.TestCase):
    _data = make_data.build(OTHER_SEED)
    lines, products = _data["order_lines"], _data["products"]


if __name__ == "__main__":
    unittest.main()
