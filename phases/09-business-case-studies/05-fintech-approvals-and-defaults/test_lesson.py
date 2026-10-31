"""Tests for case 05: loan approvals and defaults. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Every expected number is computed here in plain Python from the CSV rows, never
with SQL and never read from the solution. The checks run on the committed data,
on a second dataset built in memory with another seed, and on tiny hand-made
tables (a band nobody was lent to, open loans only, a zero rate, a tie).
"""
import csv
import importlib.util
import math
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "applications.csv")
OTHER_SEED = 8
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")

spec = importlib.util.spec_from_file_location("lesson_module", TARGET)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sys.path.insert(0, HERE)
import make_data  # noqa: E402


def read_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def run_sql(con, sql):
    body = "\n".join(ln for ln in (sql or "").splitlines() if not ln.strip().startswith("--"))
    if not body.strip():
        raise AssertionError("the query is still a TODO: write it in the exercise file")
    return m.query(con, sql)


def tiny_db(rows):
    """rows: (applied_month, score, loan_amount, outcome or None). Approved when outcome is set."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE applications (app_id TEXT, applied_month TEXT, score INTEGER,"
                " loan_amount INTEGER, decision TEXT, approval_route TEXT, outcome TEXT)")
    for i, (month, score, amount, outcome) in enumerate(rows):
        con.execute("INSERT INTO applications VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ("X%d" % i, month, score, amount, "approved" if outcome else "rejected",
                     ("policy" if score >= 650 else "test") if outcome else None, outcome))
    return con


def wilson_ref(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def band(b, applicants, matured, defaulted, rate=None, amount=30000):
    return {"band": b, "applicants": applicants, "approved": matured, "matured": matured,
            "defaulted": defaulted, "default_rate_pct": rate, "avg_amount": amount}


class TestHandMade(unittest.TestCase):
    def test_band_sql_edges(self):
        con = tiny_db([
            ("2025-05", 500, 10000, None),          # rejected: no outcome at all
            ("2025-05", 649, 20000, "defaulted"),   # 649 belongs to band 600
            ("2025-06", 650, 30000, "repaid"),      # 650 starts band 650
            ("2026-06", 655, 40000, "open"),        # approved but not finished
        ])
        got = [(r["band"], r["applicants"], r["approved"], r["matured"], r["defaulted"], r["default_rate_pct"])
               for r in run_sql(con, m.BAND_SQL)]
        self.assertEqual(got, [(500, 1, 0, 0, 0, None), (600, 1, 1, 1, 1, 100.0), (650, 2, 2, 1, 0, 0.0)],
                         "bands are score // 50 x 50; an open loan is approved but not matured; "
                         "a band with nothing matured has default_rate_pct NULL, not 0")

    def test_vintage_open_months(self):
        con = tiny_db([("2026-06", 700, 10000, "open"), ("2026-06", 600, 10000, None),
                       ("2025-07", 700, 10000, "repaid")])
        got = [(r["applied_month"], r["approved"], r["open"], r["matured"], r["defaulted"], r["default_rate_pct"])
               for r in run_sql(con, m.VINTAGE_SQL)]
        self.assertEqual(got, [("2025-07", 1, 0, 1, 0, 0.0), ("2026-06", 1, 1, 0, 0, None)],
                         "a month whose loans are all open has no default rate yet (NULL)")

    def test_wilson(self):
        self.assertIsNone(m.wilson(0, 0), "no loans: no interval")
        low, high = m.wilson(0, 20)
        self.assertAlmostEqual(low, 0.0, places=9)
        self.assertAlmostEqual(high, wilson_ref(0, 20)[1], places=9,
                               msg="0 defaults in 20 loans still has an upper bound above 0 (about 16%)")
        self.assertTrue(all(abs(a - b) < 1e-9 for a, b in zip(m.wilson(12, 69), wilson_ref(12, 69))))

    def test_cutoff_impact_simple(self):
        bands = [band(550, 30, 10, 5), band(600, 60, 20, 4), band(650, 100, 100, 3)]
        r = m.cutoff_impact(bands, 600, months=10)
        self.assertAlmostEqual(r["extra_approvals"], 6.0, msg="60 applicants in band 600 over 10 months is 6 a month")
        self.assertAlmostEqual(r["extra_defaults"], 1.2, msg="6 a month x 4/20 default rate = 1.2 defaults a month")
        self.assertAlmostEqual(r["marginal_default_rate"], 0.2)
        lo, hi = wilson_ref(4, 20)
        self.assertAlmostEqual(r["extra_defaults_low"], 6 * lo)
        self.assertAlmostEqual(r["extra_defaults_high"], 6 * hi)
        r2 = m.cutoff_impact(bands, 550, months=10)
        self.assertAlmostEqual(r2["extra_defaults"], 1.2 + 1.5, msg="each added band uses its own rate")
        self.assertAlmostEqual(r2["marginal_default_rate"], 2.7 / 9.0)

    def test_cutoff_impact_unobserved_and_no_change(self):
        bands = [band(500, 40, 0, 0), band(550, 30, 10, 5), band(650, 100, 100, 3)]
        self.assertIsNone(m.cutoff_impact(bands, 500, months=10),
                          "a band nobody was lent to has no default rate: return None, do not assume 0")
        same = m.cutoff_impact(bands, 650, months=10)
        self.assertEqual((same["extra_approvals"], same["extra_defaults"], same["marginal_default_rate"]),
                         (0.0, 0.0, None), "no band added: nothing changes")

    def test_book_rate(self):
        bands = [band(600, 50, 10, 2), band(650, 150, 100, 0)]
        self.assertAlmostEqual(m.book_default_rate(bands, 650), 0.0, msg="zero defaults is a rate of 0, not None")
        self.assertAlmostEqual(m.book_default_rate(bands, 600), 50 * 0.2 / 200,
                               msg="weight each band's rate by its applicants")
        self.assertIsNone(m.book_default_rate(bands, 700), "nobody approved: None")
        self.assertIsNone(m.book_default_rate([band(600, 5, 0, 0)], 600), "an approved band with no matured loans: None")

    def test_profit_and_break_even(self):
        self.assertAlmostEqual(m.band_profit(10, 1000, 0.0, 0.15, 0.55), 1500.0)
        self.assertAlmostEqual(m.band_profit(10, 1000, 1.0, 0.15, 0.55), -5500.0)
        be = m.break_even_rate(0.15, 0.55)
        self.assertAlmostEqual(be, 0.15 / 0.70)
        self.assertAlmostEqual(m.band_profit(10, 1000, be, 0.15, 0.55), 0.0,
                               msg="at the break-even rate the expected profit is exactly 0")

    def test_text_chart(self):
        lines = m.text_chart([band(500, 5, 0, 0, None), band(550, 5, 5, 2, 40.0), band(600, 5, 5, 1, 20.0),
                              band(650, 5, 5, 0, 0.0)], width=10)
        self.assertIn("no data", lines[0], "a band with no matured loans says 'no data', it is not drawn as 0%")
        self.assertTrue(lines[1].startswith("550-599"), "each line starts with the band label, 550-599")
        self.assertEqual([ln.count("#") for ln in lines], [0, 10, 5, 0])
        self.assertEqual(m.text_chart([]), [])


class OnDataMixin:
    path = DATA

    @classmethod
    def setUpClass(cls):
        cls.rows = read_rows(cls.path)
        cls.con = m.load_db(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.con.close()

    def expected_bands(self):
        out = {}
        for r in self.rows:
            b = out.setdefault(int(r["score"]) // 50 * 50, {"applicants": 0, "approved": 0, "matured": 0,
                                                              "defaulted": 0, "amount": 0})
            b["applicants"] += 1
            b["approved"] += r["decision"] == "approved"
            b["matured"] += r["outcome"] in ("repaid", "defaulted")
            b["defaulted"] += r["outcome"] == "defaulted"
            b["amount"] += int(r["loan_amount"])
        return out

    def test_bands(self):
        exp = self.expected_bands()
        got = run_sql(self.con, m.BAND_SQL)
        self.assertEqual([g["band"] for g in got], sorted(exp), "one row per 50-point band, in order")
        for g in got:
            e = exp[g["band"]]
            self.assertEqual((g["applicants"], g["approved"], g["matured"], g["defaulted"]),
                             (e["applicants"], e["approved"], e["matured"], e["defaulted"]),
                             "band %d: matured counts only repaid and defaulted loans, never open ones" % g["band"])
            want = round(100.0 * e["defaulted"] / e["matured"], 1) if e["matured"] else None
            if want is None:
                self.assertIsNone(g["default_rate_pct"], "band %d has nothing matured: NULL" % g["band"])
            else:
                self.assertAlmostEqual(g["default_rate_pct"], want, places=6, msg="band %d default rate" % g["band"])
            self.assertAlmostEqual(g["avg_amount"], round(e["amount"] / e["applicants"]), places=6)

    def test_vintages(self):
        exp = {}
        for r in self.rows:
            e = exp.setdefault(r["applied_month"], [0, 0, 0, 0])
            e[0] += r["decision"] == "approved"
            e[1] += r["outcome"] == "open"
            e[2] += r["outcome"] in ("repaid", "defaulted")
            e[3] += r["outcome"] == "defaulted"
        got = run_sql(self.con, m.VINTAGE_SQL)
        self.assertEqual([g["applied_month"] for g in got], sorted(exp))
        for g in got:
            e = exp[g["applied_month"]]
            self.assertEqual([g["approved"], g["open"], g["matured"], g["defaulted"]], e, g["applied_month"])

    def test_insight(self):
        exp = self.expected_bands()
        months = len({r["applied_month"] for r in self.rows})
        bands = run_sql(self.con, m.BAND_SQL)
        for new in (600, 550):
            added = [b for b in exp if new <= b < 650]
            n = sum(exp[b]["applicants"] for b in added)
            d = sum(exp[b]["applicants"] * exp[b]["defaulted"] / exp[b]["matured"] for b in added)
            hi = sum(exp[b]["applicants"] * wilson_ref(exp[b]["defaulted"], exp[b]["matured"])[1] for b in added)
            r = m.cutoff_impact(bands, new, months)
            self.assertAlmostEqual(r["extra_approvals"], n / months, places=6, msg="extra approvals a month at cutoff %d" % new)
            self.assertAlmostEqual(r["extra_defaults"], d / months, places=6, msg="extra defaults a month at cutoff %d" % new)
            self.assertAlmostEqual(r["extra_defaults_high"], hi / months, places=6)
        self.assertIsNone(m.cutoff_impact(bands, 500, months), "below 550 nobody was ever approved: None")
        cur = m.book_default_rate(bands, 650)
        low = m.book_default_rate(bands, 600)
        self.assertGreater(low, cur, "approving band 600 must raise the book's default rate")
        self.assertGreater(m.cutoff_impact(bands, 600, months)["marginal_default_rate"], low,
                           "the marginal rate of the added band is above the book's average")


class TestOnData(OnDataMixin, unittest.TestCase):
    pass


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.path = os.path.join(cls.tmp, "applications.csv")
        make_data.write_csv(make_data.build(seed=OTHER_SEED)["applications"], cls.path)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(cls.tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
