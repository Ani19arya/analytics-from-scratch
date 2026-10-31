"""Tests for lesson 06: percent vs points, ratio of sums vs average of ratios.
Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Expected answers are computed here from the raw rows with exact fractions
(fractions.Fraction), never from the solution file. The checks run on the
committed data, on a second dataset built with another seed, and on small
hand-made cases: an empty list, a day with zero visits, a day with zero
orders, equal traffic (where both methods agree) and a change from zero."""
import csv
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "daily.csv")
OTHER_SEED = 128
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


def day(date, visits, orders):
    return {"date": date, "visits": visits, "orders": orders}


def raw(path):
    with open(path, newline="") as f:
        return [(r["date"], int(r["visits"]), int(r["orders"])) for r in csv.DictReader(f)]


def expected_line(old, new):
    points = (new - old) * 100
    rel = "n/a" if old == 0 else "%+.1f%%" % float((new - old) / old * 100)
    return "%.2f%% to %.2f%%: %+.2f points (%s)" % (float(old * 100), float(new * 100), float(points), rel)


class TestToy(unittest.TestCase):
    two_days = [day("2026-10-01", 100, 10), day("2026-10-02", 900, 9)]

    def test_the_two_methods_differ(self):
        self.assertAlmostEqual(m.ratio_of_sums(self.two_days), 19 / 1000,
                               msg="ratio of sums: (10 + 9) / (100 + 900) = 1.9%")
        self.assertAlmostEqual(m.average_of_ratios(self.two_days), (0.10 + 0.01) / 2,
                               msg="average of ratios: (10% + 1%) / 2 = 5.5%")

    def test_weighted_average_equals_ratio_of_sums(self):
        self.assertAlmostEqual(m.weighted_average_of_ratios(self.two_days), m.ratio_of_sums(self.two_days),
                               msg="weighting each day's rate by its visits gives back the ratio of sums")

    def test_equal_traffic_agrees(self):
        rows = [day("2026-10-01", 500, 10), day("2026-10-02", 500, 20)]
        self.assertAlmostEqual(m.average_of_ratios(rows), m.ratio_of_sums(rows),
                               msg="with equal visits every day, the two methods agree (a tie in the weights)")

    def test_zero_visits_day(self):
        rows = [day("2026-10-01", 0, 0), day("2026-10-02", 200, 4)]
        self.assertAlmostEqual(m.ratio_of_sums(rows), 0.02)
        self.assertAlmostEqual(m.average_of_ratios(rows), 0.02,
                               msg="a day with 0 visits has no rate: skip it, do not average in a 0")
        self.assertAlmostEqual(m.weighted_average_of_ratios(rows), 0.02)

    def test_zero_orders_day_counts(self):
        rows = [day("2026-10-01", 100, 0), day("2026-10-02", 100, 4)]
        self.assertAlmostEqual(m.average_of_ratios(rows), 0.02, msg="a day with visits but 0 orders has a rate of 0")

    def test_empty(self):
        self.assertIsNone(m.ratio_of_sums([]), "no visits: no rate, return None")
        self.assertIsNone(m.average_of_ratios([]))
        self.assertIsNone(m.weighted_average_of_ratios([]))
        self.assertIsNone(m.average_of_ratios([day("2026-10-01", 0, 0)]))


class TestPointsAndPercent(unittest.TestCase):
    def test_points(self):
        self.assertAlmostEqual(m.point_change(0.02, 0.025), 0.5, msg="2% to 2.5% is +0.5 percentage points")
        self.assertAlmostEqual(m.point_change(0.025, 0.02), -0.5)

    def test_percent(self):
        self.assertAlmostEqual(m.percent_change(0.02, 0.025), 25.0, msg="2% to 2.5% is a 25% relative rise")
        self.assertAlmostEqual(m.percent_change(0.025, 0.0255), 2.0, msg="2.5% up 2% is 2.55%, not 4.5%")
        self.assertIsNone(m.percent_change(0, 0.01), "a change from 0 has no percent: return None")

    def test_describe(self):
        self.assertEqual(m.describe_change(0.02, 0.025), "2.00% to 2.50%: +0.50 points (+25.0%)")
        self.assertEqual(m.describe_change(0.025, 0.02), "2.50% to 2.00%: -0.50 points (-20.0%)",
                         "the same 0.5 points is -20% on the way down: percent depends on the starting point")
        self.assertEqual(m.describe_change(0.0, 0.01), "0.00% to 1.00%: +1.00 points (n/a)")


class OnData:
    def test_read(self):
        rows = m.read_days(self.path)
        self.assertEqual([(r["date"], r["visits"], r["orders"]) for r in rows], raw(self.path))

    def test_months(self):
        months = m.by_month(m.read_days(self.path))
        self.assertEqual(sorted(months), ["2026-09", "2026-10"])
        self.assertEqual(len(months["2026-09"]), 30)
        self.assertEqual(len(months["2026-10"]), 31)

    def test_summary(self):
        rows = raw(self.path)
        s = m.summarise(self.path)
        want = {}
        for month in ("2026-09", "2026-10"):
            days = [(v, o) for d, v, o in rows if d.startswith(month)]
            visits = sum(v for v, _ in days)
            orders = sum(o for _, o in days)
            ros = Fraction(orders, visits)
            aor = sum((Fraction(o, v) for v, o in days), Fraction(0)) / len(days)
            want[month] = (ros, aor)
            got = s[month]
            self.assertEqual((got["visits"], got["orders"]), (visits, orders))
            self.assertAlmostEqual(got["ratio_of_sums"], float(ros), places=12,
                                   msg="%s ratio of sums is total orders / total visits = %d / %d" % (month, orders, visits))
            self.assertAlmostEqual(got["average_of_ratios"], float(aor), places=12,
                                   msg="%s average of ratios is the mean of the %d daily rates" % (month, len(days)))
            self.assertAlmostEqual(m.weighted_average_of_ratios(m.by_month(m.read_days(self.path))[month]),
                                   float(ros), places=12)
        self.assertEqual(s["change_ratio_of_sums"], expected_line(want["2026-09"][0], want["2026-10"][0]))
        self.assertEqual(s["change_average_of_ratios"], expected_line(want["2026-09"][1], want["2026-10"][1]))


class TestOnData(OnData, unittest.TestCase):
    path = DATA

    def test_the_dashboards_disagree(self):
        s = m.summarise(self.path)
        self.assertLess(s["2026-10"]["ratio_of_sums"], s["2026-09"]["ratio_of_sums"])
        self.assertGreater(s["2026-10"]["average_of_ratios"], s["2026-09"]["average_of_ratios"],
                           "on this data the two methods move in opposite directions")


class TestOnSecondDataset(OnData, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.path = os.path.join(cls.tmp, "daily.csv")
        make_data.write_csv(cls.path, make_data.build(seed=OTHER_SEED)["daily"])

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_differs(self):
        self.assertNotEqual(raw(self.path), raw(DATA), "the second dataset should differ")


if __name__ == "__main__":
    unittest.main()
