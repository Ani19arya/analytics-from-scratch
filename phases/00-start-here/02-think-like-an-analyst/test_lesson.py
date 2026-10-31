"""Tests for lesson 00-02: think like an analyst.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

The expected numbers are worked out here in plain Python, from the data,
never copied from the solution. The functions also run on a second dataset
where a different city has the drop.
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

SECOND_SEED = 98
COLUMNS = ["order_id", "order_date", "city", "channel", "status", "amount"]
# The days Arjun's question is about: data runs to Thursday 29 October,
# so the like-for-like comparison is Monday to Thursday of each week.
CURRENT = ("2026-10-26", "2026-10-29")
PREVIOUS = ("2026-10-19", "2026-10-22")


def with_numbers(rows):
    return [dict(r, amount=float(r["amount"])) for r in rows]


def committed():
    with open(os.path.join(HERE, "data", "orders.csv"), newline="") as f:
        return with_numbers(csv.DictReader(f))


def second():
    return with_numbers(make_data.build(SECOND_SEED)["orders"])


def ref_total(rows, period):
    return round(sum(r["amount"] for r in rows if r["status"] == "completed" and period[0] <= r["order_date"] <= period[1]), 2)


def ref_changes(rows, column):
    out = {}
    for r in rows:
        if r["status"] != "completed":
            continue
        sign = 1 if CURRENT[0] <= r["order_date"] <= CURRENT[1] else -1 if PREVIOUS[0] <= r["order_date"] <= PREVIOUS[1] else 0
        if sign:
            out[r[column]] = out.get(r[column], 0.0) + sign * r["amount"]
    return {k: round(v, 2) for k, v in sorted(out.items())}


def ref_worst(changes):
    falling = [(v, k) for k, v in changes.items() if v < 0]
    return min(falling)[1] if falling else None


class TestPlan(unittest.TestCase):
    def test_text_fields_are_filled(self):
        for field in ("question", "decision", "metric", "metric_definition"):
            value = lesson.PLAN.get(field)
            self.assertTrue(isinstance(value, str) and len(value.strip()) >= 5,
                            "PLAN[%r] is empty: write a short sentence for it" % field)

    def test_metric_definition_says_what_is_left_out(self):
        text = lesson.PLAN["metric_definition"].lower()
        self.assertIn("cancel", text, "the metric definition should say what happens to cancelled orders")

    def test_comparison_is_like_for_like(self):
        comp = lesson.PLAN.get("comparison", {})
        self.assertEqual(tuple(comp.get("current", ())), CURRENT,
                         "current should be the days of this week that have data: Monday 26 to Thursday 29 October")
        self.assertEqual(tuple(comp.get("previous", ())), PREVIOUS,
                         "previous should be the SAME four days last week (19 to 22 October), not the whole week")

    def test_segments_and_data_are_real_columns(self):
        segments = list(lesson.PLAN.get("segments", []))
        needed = list(lesson.PLAN.get("data_needed", []))
        self.assertGreaterEqual(len(segments), 2, "name at least two columns to split sales by, such as city and channel")
        for col in segments + needed:
            self.assertIn(col, COLUMNS, "%r is not a column of orders.csv; the columns are %s" % (col, ", ".join(COLUMNS)))
        for col in ["order_date", "status", "amount"] + segments:
            self.assertIn(col, needed, "data_needed should include %r: the analysis uses it" % col)

    def test_analysis_type(self):
        self.assertEqual(lesson.PLAN.get("analysis_type", "").strip().lower(), "diagnostic",
                         "asking why sales fell is diagnostic analysis")

    def test_four_kinds_of_analysis(self):
        expected = {
            "How much did we sell last week?": "descriptive",
            "Why did sales fall in one city this week?": "diagnostic",
            "How many orders should we expect next Monday?": "predictive",
            "Should we send a discount coupon to customers in that city?": "prescriptive",
        }
        for question, kind in expected.items():
            got = lesson.ANALYSIS_TYPES.get(question, "").strip().lower()
            self.assertEqual(got, kind, "%r is %s (what happened, why, what will happen, what to do)" % (question, kind))


class TestSmallCases(unittest.TestCase):
    def test_in_period_includes_both_ends(self):
        self.assertTrue(lesson.in_period("2026-10-26", CURRENT), "the first day of the period is inside it")
        self.assertTrue(lesson.in_period("2026-10-29", CURRENT), "the last day of the period is inside it")
        self.assertFalse(lesson.in_period("2026-10-30", CURRENT), "the day after the period is outside it")
        self.assertFalse(lesson.in_period("2026-10-25", CURRENT), "the day before the period is outside it")

    def test_total_sales_skips_cancelled_and_handles_empty(self):
        rows = [
            {"order_date": "2026-10-26", "city": "A", "channel": "app", "status": "completed", "amount": 100.0},
            {"order_date": "2026-10-26", "city": "A", "channel": "app", "status": "cancelled", "amount": 500.0},
            {"order_date": "2026-10-30", "city": "A", "channel": "app", "status": "completed", "amount": 70.0},
        ]
        self.assertEqual(lesson.total_sales(rows, CURRENT), 100.0, "only completed orders inside the period count: expected 100.0")
        self.assertEqual(lesson.total_sales([], CURRENT), 0, "no orders means 0 sales")

    def test_percent_change(self):
        self.assertEqual(lesson.percent_change(90, 100), -10.0, "90 against 100 is -10.0%")
        self.assertEqual(lesson.percent_change(150, 100), 50.0, "150 against 100 is 50.0%")
        self.assertEqual(lesson.percent_change(100, 100), 0.0, "no change is 0.0%")
        self.assertIsNone(lesson.percent_change(50, 0), "when previous is 0 the change is undefined: return None")

    def test_change_by_segment_keeps_new_and_vanished_segments(self):
        rows = [
            {"order_date": "2026-10-19", "city": "Old", "channel": "app", "status": "completed", "amount": 40.0},
            {"order_date": "2026-10-27", "city": "New", "channel": "app", "status": "completed", "amount": 25.0},
            {"order_date": "2026-10-27", "city": "Old", "channel": "app", "status": "cancelled", "amount": 99.0},
        ]
        self.assertEqual(lesson.change_by_segment(rows, "city", CURRENT, PREVIOUS), {"New": 25.0, "Old": -40.0},
                         "a city with sales in only one period still needs a row, and cancelled orders do not count")
        self.assertEqual(lesson.change_by_segment([], "city", CURRENT, PREVIOUS), {}, "no orders means no segments")

    def test_biggest_drop_ties_and_no_drop(self):
        self.assertEqual(lesson.biggest_drop({"B": -5.0, "A": -5.0, "C": 3.0}), "A", "on a tie, pick the name first in A to Z order")
        self.assertEqual(lesson.biggest_drop({"A": 0.0, "B": 2.0}), None, "if nothing fell, return None")
        self.assertEqual(lesson.biggest_drop({}), None, "no segments means no drop")


class TestOnData(unittest.TestCase):
    def check(self, rows, label):
        for period in (CURRENT, PREVIOUS):
            exp = ref_total(rows, period)
            got = lesson.total_sales(rows, period)
            self.assertAlmostEqual(got, exp, delta=0.011, msg="%s: total_sales for %s gave %r, expected %.2f" % (label, period, got, exp))
        now, before = ref_total(rows, CURRENT), ref_total(rows, PREVIOUS)
        self.assertEqual(lesson.percent_change(now, before), round((now - before) / before * 100, 1), "%s: percent_change is off" % label)
        for column in ("city", "channel"):
            exp = ref_changes(rows, column)
            got = lesson.change_by_segment(rows, column, CURRENT, PREVIOUS)
            self.assertEqual(sorted(got), sorted(exp), "%s: change_by_segment(%r) should have one key per %s" % (label, column, column))
            for k in exp:
                self.assertAlmostEqual(got[k], exp[k], delta=0.011, msg="%s: change for %s %r is %r, expected %.2f" % (label, column, k, got[k], exp[k]))
            self.assertEqual(lesson.biggest_drop(got), ref_worst(exp), "%s: the %s with the biggest drop should be %r" % (label, column, ref_worst(exp)))

    def test_lesson_data(self):
        self.check(committed(), "lesson data")

    def test_second_dataset(self):
        self.check(second(), "second dataset")


if __name__ == "__main__":
    unittest.main()
