"""Tests for lesson 07: dashboard design and KPI cards.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

Expected KPI values are computed here in plain Python from the raw rows, with the period
dates written out by hand. The cards are checked on the committed data (as of 20 October)
and on a second dataset from make_data.build(seed=2032, end=13 October) built in memory,
so code that hard-codes the 20th or the committed totals fails. Small cases cover month
ends, January, a leap year, no orders, every order refunded, and a zero prior period.
"""
import importlib.util
import os
import unittest
import xml.etree.ElementTree as ET
from datetime import date, timedelta

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
NS = "{http://www.w3.org/2000/svg}"
D = date


def as_rows(raw):
    return [{"order_id": str(r["order_id"]), "order_date": D.fromisoformat(r["order_date"]), "city": r["city"],
             "amount": float(r["amount"]), "refunded": r["refunded"] == 1} for r in raw]


def ref_kpis(rows, start, end, city=None):
    n = paid = 0
    revenue = 0.0
    day = start
    days = set()
    while day <= end:
        days.add(day)
        day += timedelta(days=1)
    for r in rows:
        if r["order_date"] in days and (city is None or r["city"] == city):
            n += 1
            if not r["refunded"]:
                paid += 1
                revenue += r["amount"]
    return {"revenue": revenue, "orders": n, "aov": revenue / paid if paid else None,
            "refund_rate": (n - paid) / n * 100 if n else None}


def small_order(day, amount, refunded=False, city="Pune"):
    return {"order_id": "x", "order_date": day, "city": city, "amount": amount, "refunded": refunded}


class TestPeriods(unittest.TestCase):
    def test_period_bounds(self):
        cases = {
            D(2026, 10, 20): (D(2026, 10, 1), D(2026, 10, 20), D(2026, 9, 1), D(2026, 9, 20)),
            D(2026, 10, 1): (D(2026, 10, 1), D(2026, 10, 1), D(2026, 9, 1), D(2026, 9, 1)),
            D(2026, 3, 30): (D(2026, 3, 1), D(2026, 3, 30), D(2026, 2, 1), D(2026, 2, 28)),
            D(2026, 3, 31): (D(2026, 3, 1), D(2026, 3, 31), D(2026, 2, 1), D(2026, 2, 28)),
            D(2026, 4, 30): (D(2026, 4, 1), D(2026, 4, 30), D(2026, 3, 1), D(2026, 3, 31)),
            D(2026, 1, 15): (D(2026, 1, 1), D(2026, 1, 15), D(2025, 12, 1), D(2025, 12, 15)),
            D(2024, 3, 29): (D(2024, 3, 1), D(2024, 3, 29), D(2024, 2, 1), D(2024, 2, 29)),
        }
        for as_of, want in cases.items():
            self.assertEqual(tuple(lesson.period_bounds(as_of)), want,
                             "period_bounds(%s): the same days of the month before, capped at its length, "
                             "and the whole previous month once the current month is complete" % as_of)

    def test_paced_target(self):
        self.assertAlmostEqual(lesson.paced_target(310000, D(2026, 10, 20)), 200000)
        self.assertAlmostEqual(lesson.paced_target(280, D(2026, 2, 28)), 280)
        self.assertAlmostEqual(lesson.paced_target(300, D(2026, 9, 1)), 10)


class TestKpisAndChange(unittest.TestCase):
    def test_no_orders(self):
        got = lesson.kpis([], D(2026, 10, 1), D(2026, 10, 20))
        self.assertEqual((got["revenue"], got["orders"], got["aov"], got["refund_rate"]), (0, 0, None, None),
                         "no orders: revenue 0, orders 0, and the two ratios are None, not 0")

    def test_refunds_and_zero_amounts(self):
        rows = [small_order(D(2026, 10, 2), 100.0), small_order(D(2026, 10, 3), 0.0),
                small_order(D(2026, 10, 3), 50.0, refunded=True), small_order(D(2026, 9, 30), 999.0)]
        got = lesson.kpis(rows, D(2026, 10, 1), D(2026, 10, 31))
        self.assertEqual((got["revenue"], got["orders"], got["aov"]), (100.0, 3, 50.0),
                         "revenue counts orders not refunded; a zero order still counts; 30 Sep is outside")
        self.assertAlmostEqual(got["refund_rate"], 100 / 3, places=2)
        all_refunded = lesson.kpis([small_order(D(2026, 10, 2), 80.0, refunded=True)], D(2026, 10, 1), D(2026, 10, 2))
        self.assertEqual((all_refunded["revenue"], all_refunded["aov"], all_refunded["refund_rate"]), (0, None, 100.0))

    def test_city_filter(self):
        rows = [small_order(D(2026, 10, 2), 10.0, city="Pune"), small_order(D(2026, 10, 2), 30.0, city="Nashik")]
        self.assertEqual(lesson.kpis(rows, D(2026, 10, 1), D(2026, 10, 2), city="Nashik")["revenue"], 30.0)

    def test_change(self):
        self.assertEqual(lesson.change("amount", 110, 100), 10.0)
        self.assertEqual(lesson.change("amount", 100, 100), 0.0, "a tie is a change of 0, not None")
        self.assertIsNone(lesson.change("amount", 5, 0), "percent change from 0 is undefined")
        self.assertIsNone(lesson.change("amount", None, 5))
        self.assertEqual(lesson.change("rate", 5.0, 4.0), 1.0, "a rate changes in percentage points, not percent")
        self.assertEqual(lesson.change("rate", 0.0, 0.0), 0.0)
        self.assertIsNone(lesson.change("rate", 3.0, None))


class CardChecks:
    rows = targets = as_of = None

    def check_cards(self, city):
        cards = lesson.kpi_cards(self.rows, self.as_of, self.targets, city)
        self.assertEqual([c["kpi"] for c in cards], ["revenue", "orders", "aov", "refund_rate"])
        cur_start = self.as_of.replace(day=1)
        prior_end = cur_start - timedelta(days=1)
        prior_start = prior_end.replace(day=1)
        prior_end = prior_start.replace(day=min(self.as_of.day, prior_end.day))
        cur = ref_kpis(self.rows, cur_start, self.as_of, city)
        pri = ref_kpis(self.rows, prior_start, prior_end, city)
        month_days = 31 if self.as_of.month in (1, 3, 5, 7, 8, 10, 12) else 30
        month_targets = self.targets.get(self.as_of.strftime("%Y-%m"), {}) if city is None else {}
        for card in cards:
            k = card["kpi"]
            self.assertAlmostEqual(card["value"], cur[k], places=1, msg="%s: value for 1 to %d of the month" % (k, self.as_of.day))
            self.assertAlmostEqual(card["prior"], pri[k], places=1,
                                   msg="%s: the prior value must cover the same days of last month, not all of it" % k)
            if k == "refund_rate":
                self.assertAlmostEqual(card["change"], cur[k] - pri[k], places=1, msg="refund rate change in points")
                self.assertEqual(card["change_unit"], "pts")
            else:
                self.assertAlmostEqual(card["change"], (cur[k] - pri[k]) / pri[k] * 100, places=0, msg="%s: percent change" % k)
                self.assertEqual(card["change_unit"], "%")
            self.assertEqual(card["small_n"], cur["orders"] < 30)
            self.assertEqual(card["n"], cur["orders"])
            if k in month_targets and k != "refund_rate":
                pace = month_targets[k] * self.as_of.day / month_days
                self.assertAlmostEqual(card["vs_target"], cur[k] / pace * 100, places=0,
                                       msg="%s: value as a percent of the paced target" % k)
                self.assertEqual(card["status"], "on track" if cur[k] >= pace else "behind")
            elif k == "refund_rate" and k in month_targets:
                self.assertAlmostEqual(card["vs_target"], cur[k] - month_targets[k], places=1)
                self.assertEqual(card["status"], "on track" if cur[k] <= month_targets[k] else "behind",
                                 "a refund rate is on track when it is at or under the limit")
            else:
                self.assertIsNone(card["vs_target"], "%s: no target, so vs_target is None" % k)
                self.assertIsNone(card["status"])
        return cards

    def test_company_cards(self):
        cards = self.check_cards(None)
        self.assertFalse(any(c["small_n"] for c in cards))

    def test_nashik_cards_are_small_n_and_have_no_target(self):
        cards = self.check_cards("Nashik")
        self.assertTrue(all(c["small_n"] for c in cards), "Nashik has under 30 orders, so every card is flagged")


class TestCommittedData(CardChecks, unittest.TestCase):
    rows = lesson.load_orders()
    targets = lesson.load_targets()
    as_of = D(2026, 10, 20)

    def test_partial_month_is_not_compared_with_a_full_month(self):
        revenue = lesson.kpi_cards(self.rows, self.as_of, self.targets)[0]
        full_sep = ref_kpis(self.rows, D(2026, 9, 1), D(2026, 9, 30))["revenue"]
        self.assertGreater(revenue["change"], 0, "1-20 Oct vs 1-20 Sep is up; against all of September it looks down")
        self.assertLess(revenue["value"], full_sep)


class TestSecondDataset(CardChecks, unittest.TestCase):
    """Another seed, ending on 13 October, built in memory."""
    _data = make_data.build(seed=2032, end=D(2026, 10, 13))
    rows = as_rows(_data["orders"])
    targets = {}
    for t in _data["targets"]:
        targets.setdefault(t["month"], {})[t["kpi"]] = float(t["target"])
    as_of = D(2026, 10, 13)


class TestSvg(unittest.TestCase):
    def test_render_svg(self):
        rows = [small_order(D(2026, 10, 1), 200.0), small_order(D(2026, 9, 1), 100.0, refunded=True)]
        cards = lesson.kpi_cards(rows, D(2026, 10, 1), {"2026-10": {"revenue": 3100.0, "orders": 31.0, "refund_rate": 4.0}})
        svg = lesson.render_svg(cards, 'Tiffinbell & "friends"', "1 Oct 2026")
        root = ET.fromstring(svg)

        def texts(cls):
            return [e.text for e in root.iter(NS + "text") if e.get("class") == cls]
        self.assertEqual([e.get("data-kpi") for e in root.iter(NS + "rect") if e.get("class") == "card"],
                         ["revenue", "orders", "aov", "refund_rate"])
        self.assertEqual(texts("title"), ['Tiffinbell & "friends"'])
        self.assertEqual(texts("card-label"), [c["label"] for c in cards])
        self.assertEqual(texts("card-value"), [lesson.fmt_value(c) for c in cards])
        self.assertEqual(texts("card-change"), [lesson.change_text(c) for c in cards])
        self.assertEqual(len(texts("card-small-n")), 4, "one order is a small n: every card carries the note")
        self.assertIn("no comparison", texts("card-change")[0], "prior revenue is 0 (its one order was refunded), so there is no percent change to show")

    def test_no_small_n_note_when_not_flagged(self):
        rows = [small_order(D(2026, 10, 1), 10.0) for _ in range(40)]
        svg = lesson.render_svg(lesson.kpi_cards(rows, D(2026, 10, 1), {}), "T")
        root = ET.fromstring(svg)
        self.assertEqual([e for e in root.iter(NS + "text") if e.get("class") == "card-small-n"], [])


if __name__ == "__main__":
    unittest.main()
