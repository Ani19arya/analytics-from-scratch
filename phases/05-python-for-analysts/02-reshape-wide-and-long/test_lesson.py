"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py.

Expected answers are computed here in plain Python, never read from the solution.
"""
import csv
import importlib.util
import os
import random
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_data  # noqa: E402

TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)

OTHER_SEED = 2027


def long_rows():
    with open(os.path.join(HERE, "data", "sales_long.csv"), newline="") as f:
        return list(csv.DictReader(f))


def reference_wide(rows, index, columns, values):
    """Plain reference: first-appearance order, "" where a pair is missing."""
    row_keys, col_keys, cells = [], [], {}
    for r in rows:
        if r[index] not in row_keys:
            row_keys.append(r[index])
        if r[columns] not in col_keys:
            col_keys.append(r[columns])
        cells[(r[index], r[columns])] = r[values]
    wide = [dict([(index, i)] + [(c, cells.get((i, c), "")) for c in col_keys]) for i in row_keys]
    return [index] + col_keys, wide


def sorted_rows(rows):
    return sorted((r["region"], r["month"], r["revenue"]) for r in rows)


class TestReshapeOnData(unittest.TestCase):
    def check_dataset(self, rows, label):
        header, wide = lesson.pivot_wider(rows, "region", "month", "revenue")
        want_header, want_wide = reference_wide(rows, "region", "month", "revenue")
        self.assertEqual(header, want_header, "%s: header must list months in order of first appearance" % label)
        self.assertEqual(wide, want_wide, "%s: wide table differs from the plain reference" % label)
        back = lesson.pivot_longer(wide, "region", "month", "revenue")
        self.assertEqual(sorted_rows(back), sorted_rows(rows),
                         "%s: the round trip must give back the same rows (in any order)" % label)
        self.assertTrue(lesson.same_rows(back, rows), "%s: same_rows should say True after a round trip" % label)
        months = {}
        for r in rows:
            months[r["month"]] = months.get(r["month"], 0) + int(r["revenue"])
        self.assertEqual(lesson.total_by(rows, "month", "revenue"), months, "%s: total_by month is wrong" % label)

    def test_committed_file(self):
        rows = long_rows()
        self.assertEqual(len(rows), 23)
        self.check_dataset(rows, "committed file")
        header, wide = lesson.pivot_wider(rows, "region", "month", "revenue")
        self.assertEqual(header, ["region", "Jan", "Feb", "Mar", "Apr", "May", "Jun"])
        self.assertEqual([r["region"] for r in wide], ["North", "South", "East", "West"])
        self.assertEqual(wide[3]["Mar"], "", "West has no March row, so the cell must be empty, not 0")

    def test_second_dataset_shuffled(self):
        """Another seed, built in memory and shuffled, so the input is not sorted by region and month."""
        rows = make_data.build(OTHER_SEED)["sales_long"]
        random.Random(OTHER_SEED).shuffle(rows)
        self.check_dataset(rows, "seed %d, shuffled" % OTHER_SEED)
        _, wide = lesson.pivot_wider(rows, "region", "month", "revenue")
        back = lesson.pivot_longer(wide, "region", "month", "revenue")
        self.assertNotEqual(back, rows, "shuffled input comes back in wide order, which is why you compare as sets of rows")

    def test_other_axis(self):
        rows = long_rows()
        header, wide = lesson.pivot_wider(rows, "month", "region", "revenue")
        self.assertEqual(header, ["month", "North", "South", "East", "West"])
        self.assertEqual(len(wide), 6)


class TestReshapeSmall(unittest.TestCase):
    def test_empty_input(self):
        self.assertEqual(lesson.pivot_wider([], "region", "month", "revenue"), (["region"], []))
        self.assertEqual(lesson.pivot_longer([], "region", "month", "revenue"), [])
        self.assertEqual(lesson.total_by([], "month", "revenue"), {})
        self.assertTrue(lesson.same_rows([], []))

    def test_zero_is_kept(self):
        wide = [{"region": "North", "Jan": "0", "Feb": ""}]
        self.assertEqual(lesson.pivot_longer(wide, "region", "month", "revenue"),
                         [{"region": "North", "month": "Jan", "revenue": "0"}],
                         "a 0 is a real observation and stays; only the empty cell is skipped")

    def test_duplicate_pair_raises(self):
        rows = long_rows() + [{"region": "North", "month": "Jan", "revenue": "1"}]
        with self.assertRaises(ValueError):
            lesson.pivot_wider(rows, "region", "month", "revenue")

    def test_duplicate_pair_summed_only_when_asked(self):
        rows = [{"region": "North", "month": "Jan", "revenue": "10"},
                {"region": "North", "month": "Jan", "revenue": "5"},
                {"region": "South", "month": "Feb", "revenue": "7"}]
        header, wide = lesson.pivot_wider(rows, "region", "month", "revenue", duplicates="sum")
        self.assertEqual(header, ["region", "Jan", "Feb"])
        self.assertEqual(wide, [{"region": "North", "Jan": "15", "Feb": ""}, {"region": "South", "Jan": "", "Feb": "7"}],
                         "duplicates='sum' adds the two North Jan rows, like a pivot table set to Sum")
        with self.assertRaises(ValueError):
            lesson.pivot_wider(rows, "region", "month", "revenue", duplicates="last")

    def test_same_rows_counts_repeats(self):
        a = [{"k": "1"}, {"k": "1"}, {"k": "2"}]
        self.assertTrue(lesson.same_rows(a, list(reversed(a))))
        self.assertFalse(lesson.same_rows(a, [{"k": "1"}, {"k": "2"}, {"k": "2"}]),
                         "same_rows must count how often each row appears, not only which rows appear")


if __name__ == "__main__":
    unittest.main()
