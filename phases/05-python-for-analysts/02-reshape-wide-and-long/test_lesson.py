"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py."""
import csv
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)


def long_rows():
    with open(os.path.join(HERE, "data", "sales_long.csv"), newline="") as f:
        return list(csv.DictReader(f))


class TestReshape(unittest.TestCase):
    def test_wide_shape_and_cells(self):
        rows = long_rows()
        header, wide = lesson.pivot_wider(rows, "region", "month", "revenue")
        self.assertEqual(header, ["region", "Jan", "Feb", "Mar", "Apr", "May", "Jun"])
        self.assertEqual([r["region"] for r in wide], ["North", "South", "East", "West"])
        north_apr = [r["revenue"] for r in rows if r["region"] == "North" and r["month"] == "Apr"][0]
        self.assertEqual(wide[0]["Apr"], north_apr)
        self.assertEqual(wide[3]["Mar"], "", "West has no March row, so the cell must be empty")

    def test_round_trip(self):
        rows = long_rows()
        _, wide = lesson.pivot_wider(rows, "region", "month", "revenue")
        back = lesson.pivot_longer(wide, "region", "month", "revenue")
        self.assertEqual(len(back), 23)
        self.assertEqual(back, rows)

    def test_other_axis(self):
        rows = long_rows()
        header, wide = lesson.pivot_wider(rows, "month", "region", "revenue")
        self.assertEqual(header, ["month", "North", "South", "East", "West"])
        self.assertEqual(len(wide), 6)

    def test_duplicate_pair_raises(self):
        rows = long_rows() + [{"region": "North", "month": "Jan", "revenue": "1"}]
        with self.assertRaises(ValueError):
            lesson.pivot_wider(rows, "region", "month", "revenue")

    def test_total_by(self):
        rows = long_rows()
        by_month = lesson.total_by(rows, "month", "revenue")
        self.assertEqual(sum(by_month.values()), sum(int(r["revenue"]) for r in rows))
        self.assertEqual(by_month["Mar"], sum(int(r["revenue"]) for r in rows if r["month"] == "Mar"))
        self.assertEqual(len(lesson.total_by(rows, "region", "revenue")), 4)


if __name__ == "__main__":
    unittest.main()
