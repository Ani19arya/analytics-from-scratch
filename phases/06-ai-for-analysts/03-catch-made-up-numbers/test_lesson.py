"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py."""
import csv
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lesson = load("lesson", TARGET)
make_data = load("make_data", os.path.join(HERE, "make_data.py"))
OTHER_SEED = 1603
MINUS = "\u2212"


def read(name):
    with open(os.path.join(HERE, "data", name), newline="") as f:
        return list(csv.DictReader(f))


class TestExtract(unittest.TestCase):
    def test_extract_simple(self):
        got = lesson.extract_numbers("Revenue was $156,142 from 240 orders, up 30.6% on 1.50 per unit.")
        self.assertEqual(got, [(156142.0, 0), (240.0, 0), (30.6, 1), (1.5, 2)])

    def test_extract_sentence_end_and_none(self):
        self.assertEqual(lesson.extract_numbers("West made $52,000."), [(52000.0, 0)])
        self.assertEqual(lesson.extract_numbers("No numbers here."), [])
        self.assertEqual(lesson.extract_numbers(""), [])

    def test_years_and_period_labels_are_not_numbers(self):
        self.assertEqual(lesson.extract_numbers("In H1 2026 revenue fell 3.2% to $1.5M."), [(3.2, 1), (1500000.0, -5)],
                         "H1 and 2026 are labels, and $1.5M is 1,500,000 stated to the nearest 100,000")
        self.assertEqual(lesson.extract_numbers("Q3 2025 and FY26 were the 2nd best periods."), [])

    def test_negatives(self):
        self.assertEqual(lesson.extract_numbers("Margin moved -4.1% in May."), [(-4.1, 1)], "keep the minus sign")
        self.assertEqual(lesson.extract_numbers("Margin moved " + MINUS + "4.1% in May."), [(-4.1, 1)],
                         "LLMs often write the Unicode minus sign")
        self.assertEqual(lesson.extract_numbers("Up +3.4% on April."), [(3.4, 1)])
        self.assertEqual(lesson.extract_numbers("Delivery took 3-5 days."), [(3.0, 0), (5.0, 0)],
                         "the dash in a range is not a minus sign")

    def test_suffixes(self):
        self.assertEqual(lesson.extract_numbers("South brought in $50k."), [(50000.0, -3)])
        self.assertEqual(lesson.extract_numbers("Q2 revenue was $77.9k."), [(77900.0, -2)])
        self.assertEqual(lesson.extract_numbers("Sales hit 1.2 million and $2bn."), [(1200000.0, -5), (2000000000.0, -9)])
        self.assertEqual(lesson.extract_numbers("It took 5 months."), [(5.0, 0)], "the m in months is not a million")

    def test_a_comma_number_is_never_a_year(self):
        self.assertEqual(lesson.extract_numbers("We shipped 2,026 orders."), [(2026.0, 0)])

    def test_precision_with_a_suffix(self):
        self.assertTrue(lesson.matches(51000.0, -3, 51319), "$51k allows 500 either way")
        self.assertFalse(lesson.matches(52000.0, 0, 51319), "52,000 with no suffix is read as exact")
        self.assertTrue(lesson.matches(-0.5, 1, -0.53))
        self.assertFalse(lesson.matches(0.5, 1, -0.53), "a lost minus sign is a wrong number")


class TestCheckSummary(unittest.TestCase):
    def test_mismatched_counts_raise(self):
        rows = read("orders.csv")
        bad = [{"sentence_id": "X", "metrics": "total_revenue;order_count", "sentence": "Revenue was 5."}]
        with self.assertRaises(ValueError):
            lesson.check_summary(rows, bad)

    def test_empty_summary(self):
        self.assertEqual(lesson.check_summary(read("orders.csv"), []), [])

    def test_flags_exactly_the_fabricated_numbers(self):
        rows = read("orders.csv")
        results = lesson.check_summary(rows, read("ai_summary.csv"))
        self.assertEqual(len(results), 15)
        flagged = sorted((r["sentence_id"], r["metric"]) for r in results if not r["ok"])
        self.assertEqual(flagged, [("S3", "north_share_pct"), ("S4", "west_revenue"), ("S5", "growth_pct")])

    def test_actuals_are_independent_of_the_text(self):
        rows = read("orders.csv")
        results = lesson.check_summary(rows, read("ai_summary.csv"))
        by = {r["metric"]: r for r in results}
        self.assertEqual(by["total_revenue"]["actual"], sum(int(r["revenue"]) for r in rows))
        self.assertEqual(by["west_revenue"]["actual"], sum(int(r["revenue"]) for r in rows if r["region"] == "West"))
        self.assertEqual(by["west_revenue"]["claimed"], 52000.0)
        self.assertEqual(by["q2_vs_q1_pct"]["claimed"], -0.5)
        self.assertEqual(by["q2_revenue"]["claimed"], 77900.0)

    def test_second_dataset(self):
        built = make_data.build(seed=OTHER_SEED)
        rows = [{k: str(v) for k, v in r.items()} for r in built["orders"]]
        results = lesson.check_summary(rows, built["summary"])
        flagged = sorted((r["sentence_id"], r["metric"]) for r in results if not r["ok"])
        self.assertEqual(flagged, sorted(built["fabricated"]),
                         "seed %d: the checker should flag exactly the numbers made wrong on purpose" % OTHER_SEED)
        by = {r["metric"]: r for r in results}
        q1 = sum(int(r["revenue"]) for r in rows if r["month"] in ("Jan", "Feb", "Mar"))
        q2 = sum(int(r["revenue"]) for r in rows if r["month"] in ("Apr", "May", "Jun"))
        self.assertEqual(by["q2_revenue"]["actual"], q2)
        self.assertAlmostEqual(by["q2_vs_q1_pct"]["actual"], (q2 - q1) / q1 * 100)
        self.assertEqual(by["order_count"]["actual"], len(rows))


if __name__ == "__main__":
    unittest.main()
