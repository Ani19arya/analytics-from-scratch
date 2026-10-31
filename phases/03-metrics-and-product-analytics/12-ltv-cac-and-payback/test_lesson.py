"""Tests for lesson 12: unit economics, LTV, CAC and payback. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Every expected number is computed here in plain Python, never read from the solution.
The tests run on the committed data and on a second dataset built with another seed."""
import csv
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
AS_OF = "2026-10"
MARGIN = 0.70
OTHER_SEED = 3
CHANNELS = ("paid_social", "search", "referral")
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")


def load():
    spec = importlib.util.spec_from_file_location("lesson_module", TARGET)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load()
sys.path.insert(0, HERE)
import make_data  # noqa: E402


def month_index(text):
    return int(text[:4]) * 12 + int(text[5:]) - 1


def reference(folder):
    """Independent route: each customer's payments as a list sorted by month. Because a
    customer pays every month until they cancel, lifetime = number of payments, and the
    customer churned if their last payment is before the as-of month."""
    with open(os.path.join(folder, "customers.csv"), newline="") as f:
        cust = {r["customer_id"]: r for r in csv.DictReader(f)}
    pays = {}
    with open(os.path.join(folder, "payments.csv"), newline="") as f:
        for r in csv.DictReader(f):
            pays.setdefault(r["customer_id"], []).append((r["month"], float(r["amount"])))
    spend = {}
    with open(os.path.join(folder, "spend.csv"), newline="") as f:
        for r in csv.DictReader(f):
            spend[r["channel"]] = spend.get(r["channel"], 0.0) + float(r["spend"])
    out = {}
    for ch in CHANNELS:
        ids = [c for c, r in cust.items() if r["channel"] == ch]
        rev = sum(a for c in ids for _, a in pays.get(c, []))
        months = sum(len(pays.get(c, [])) for c in ids)
        churned = sum(1 for c in ids if pays.get(c) and max(pays[c])[0] < AS_OF)
        at_risk = months - sum(1 for c in ids if pays.get(c) and max(pays[c])[0] == AS_OF)
        arpu, churn = rev / months, churned / at_risk
        ages = {c: month_index(AS_OF) - month_index(cust[c]["signup_month"]) + 1 for c in ids}
        curve = {}
        for n in range(1, max(ages.values()) + 1):
            elig = [c for c in ids if ages[c] >= n]
            curve[n] = sum(a for c in elig for _, a in sorted(pays.get(c, []))[:n]) * MARGIN / len(elig)
        k = spend[ch] / len(ids)
        payback = next((n for n in sorted(curve) if curve[n] >= k), None)
        out[ch] = {"cac": k, "arpu": arpu, "churn": churn, "ltv": arpu * MARGIN / churn,
                   "curve": curve, "payback": payback}
    return out


def tables(customers, payments, spend=None):
    cust = {c: (s, ch) for c, s, ch in customers}
    pays = {}
    for c, month, amount in payments:
        pays.setdefault(c, {})[month] = amount
    return cust, pays, spend or {}


class TestSmallCases(unittest.TestCase):
    def test_cac(self):
        cust, _, spend = tables([("a", "2026-01", "search"), ("b", "2026-02", "search")], [],
                                {"search": 90.0, "brand": 500.0})
        self.assertAlmostEqual(m.cac(spend, cust, "search"), 45.0)
        self.assertIsNone(m.cac(spend, cust, "brand"),
                          "brand spend has no customers of its own: its CAC is None, not a division error")
        self.assertEqual(m.cac({}, cust, "search"), 0.0, "no spend with customers is a CAC of 0")

    def test_churn_and_censoring(self):
        # a pays Aug to Oct and is still active; b pays Aug and Sep, then cancels; c pays Oct only
        cust, pays, _ = tables([("a", "2026-08", "x"), ("b", "2026-08", "x"), ("c", "2026-10", "x")],
                               [("a", "2026-08", 10.0), ("a", "2026-09", 10.0), ("a", "2026-10", 10.0),
                                ("b", "2026-08", 20.0), ("b", "2026-09", 20.0), ("c", "2026-10", 10.0)])
        arpu, churn = m.arpu_and_churn(cust, pays, "x", "2026-10")
        self.assertAlmostEqual(arpu, 80.0 / 6)
        self.assertAlmostEqual(churn, 1 / 4, msg="1 cancel out of 4 paid months that could renew; "
                                                  "October payments cannot renew yet, so leave them out")

    def test_year_boundary(self):
        cust, pays, _ = tables([("a", "2025-12", "x")], [("a", "2025-12", 10.0), ("a", "2026-01", 10.0)])
        self.assertEqual(m.arpu_and_churn(cust, pays, "x", "2026-02")[1], 0.5,
                         "December's next month is January: December renewed, January did not, so churn is 1 / 2")
        self.assertEqual(m.months_between("2025-11", "2026-02"), 3)

    def test_ltv(self):
        self.assertAlmostEqual(m.margin_ltv(15.0, 0.10, 0.70), 105.0)
        self.assertIsNone(m.margin_ltv(15.0, 0.0, 0.70), "zero observed churn: LTV is not infinite, it is unknown")
        self.assertIsNone(m.margin_ltv(None, 0.1, 0.70))
        self.assertEqual(m.arpu_and_churn({}, {}, "x", "2026-10"), (None, None), "an empty channel has no ARPU or churn")

    def test_curve(self):
        # a: 3 months observed, cancelled after 1; b: 2 months observed, still paying
        cust, pays, _ = tables([("a", "2026-08", "x"), ("b", "2026-09", "x")],
                               [("a", "2026-08", 10.0), ("b", "2026-09", 20.0), ("b", "2026-10", 20.0)])
        curve = m.margin_curve(cust, pays, "x", 0.5, "2026-10")
        self.assertEqual(sorted(curve), [1, 2, 3])
        self.assertAlmostEqual(curve[1], (5.0 + 10.0) / 2)
        self.assertAlmostEqual(curve[2], (5.0 + 20.0) / 2, msg="a cancelled customer still counts, with what they paid")
        self.assertAlmostEqual(curve[3], 5.0, msg="only a is old enough for month 3; b is left out, not counted as 0")
        self.assertEqual(m.margin_curve(cust, pays, "nobody", 0.5, "2026-10"), {})

    def test_payback(self):
        curve = {1: 10.0, 2: 20.0, 3: 30.0}
        self.assertEqual(m.payback_months(curve, 20.0), 2, "reaching CAC exactly counts as paid back")
        self.assertEqual(m.payback_months(curve, 5.0), 1)
        self.assertIsNone(m.payback_months(curve, 31.0), "never reached within the data: None")
        self.assertIsNone(m.payback_months({}, 5.0))
        self.assertIsNone(m.payback_months(curve, None))


class OnDataMixin:
    folder = DATA

    def test_channels(self):
        ref = reference(self.folder)
        customers, payments, spend = m.load(self.folder)
        for ch in CHANNELS:
            r = ref[ch]
            self.assertAlmostEqual(m.cac(spend, customers, ch), r["cac"], places=6,
                                   msg="%s CAC: expected %.2f" % (ch, r["cac"]))
            arpu, churn = m.arpu_and_churn(customers, payments, ch)
            self.assertAlmostEqual(arpu, r["arpu"], places=9, msg="%s ARPU: expected %.4f" % (ch, r["arpu"]))
            self.assertAlmostEqual(churn, r["churn"], places=9, msg="%s churn: expected %.4f" % (ch, r["churn"]))
            self.assertAlmostEqual(m.margin_ltv(arpu, churn), r["ltv"], places=6)

    def test_curve_and_payback(self):
        ref = reference(self.folder)
        customers, payments, spend = m.load(self.folder)
        for ch in CHANNELS:
            curve = m.margin_curve(customers, payments, ch)
            self.assertEqual(sorted(curve), sorted(ref[ch]["curve"]), "%s: wrong months in the curve" % ch)
            for n, want in ref[ch]["curve"].items():
                self.assertAlmostEqual(curve[n], want, places=9, msg="%s month %d: expected %.3f" % (ch, n, want))
            self.assertEqual(m.payback_months(curve, m.cac(spend, customers, ch)), ref[ch]["payback"],
                             "%s payback: expected %s" % (ch, ref[ch]["payback"]))


class TestOnData(OnDataMixin, unittest.TestCase):
    def test_story(self):
        ref = reference(self.folder)
        self.assertLess(ref["paid_social"]["ltv"], ref["paid_social"]["cac"])


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.folder = cls.tmp
        make_data.write_all(make_data.build(seed=OTHER_SEED), cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
