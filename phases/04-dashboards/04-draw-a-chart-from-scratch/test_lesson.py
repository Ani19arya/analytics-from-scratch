"""Tests for lesson 04: draw a chart from scratch.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

"""
import csv
import importlib.util
import os
import unittest
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
if os.environ.get("CHECK_SOLUTION") == "1":
    PY_FILE = os.path.join(HERE, "solution", "solution.py")
else:
    PY_FILE = os.path.join(HERE, "exercise.py")

spec = importlib.util.spec_from_file_location("chart", PY_FILE)
chart = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chart)

NS = "{http://www.w3.org/2000/svg}"
PLOT_HEIGHT, BASELINE = 300, 340


def read_rows():
    with open(os.path.join(HERE, "data", "product_line_revenue.csv"), newline="") as f:
        return [(r["product_line"], int(r["revenue"])) for r in csv.DictReader(f)]


def parse(svg):
    root = ET.fromstring(svg)
    def find(tag, cls):
        return [e for e in root.iter(NS + tag) if e.get("class") == cls]
    return root, find


class TestHelpers(unittest.TestCase):
    def test_nice_max(self):
        cases = {7: 10, 42: 50, 1234: 2000, 200: 200, 0.3: 0.5, 18.5: 20, 23: 25, 1: 1, 38900: 50000, 0: 1}
        for value, want in cases.items():
            self.assertAlmostEqual(chart.nice_max(value), want, msg="nice_max(%r)" % value)

    def test_axis_ticks(self):
        self.assertEqual([float(t) for t in chart.axis_ticks(50000)], [0, 10000, 20000, 30000, 40000, 50000])
        for got, want in zip(chart.axis_ticks(2.5), [0, 0.5, 1, 1.5, 2, 2.5]):
            self.assertAlmostEqual(got, want)

    def test_sort_rows(self):
        rows = [("B", 5), ("A", 5), ("C", 9), ("D", 1)]
        self.assertEqual(chart.sort_rows(rows), [("C", 9), ("A", 5), ("B", 5), ("D", 1)])

    def test_choose_chart(self):
        self.assertEqual(chart.choose_chart("time"), "line")
        self.assertEqual(chart.choose_chart("category"), "bar")
        with self.assertRaises(ValueError):
            chart.choose_chart("3d pie")


class TestBarChart(unittest.TestCase):
    def setUp(self):
        self.rows = read_rows()
        self.svg = chart.bar_chart_svg(self.rows, "Revenue by product line, 2025")
        self.root, self.find = parse(self.svg)

    def test_is_valid_svg_with_title(self):
        self.assertEqual(self.root.tag, NS + "svg")
        titles = self.find("text", "title")
        self.assertEqual([t.text for t in titles], ["Revenue by product line, 2025"])

    def test_one_bar_per_row_sorted_largest_first(self):
        bars = self.find("rect", "bar")
        want = sorted(self.rows, key=lambda r: (-r[1], r[0]))
        self.assertEqual([b.get("data-label") for b in bars], [r[0] for r in want])
        xs = [float(b.get("x")) for b in bars]
        self.assertEqual(xs, sorted(xs), "bars must run left to right in sorted order")

    def test_bar_heights_scale_from_zero(self):
        axis_max = 50000  # nice_max of the largest value, 38,900
        self.assertEqual(max(v for _, v in self.rows), 38900)
        for b in self.find("rect", "bar"):
            value = float(b.get("data-value"))
            h, y = float(b.get("height")), float(b.get("y"))
            self.assertAlmostEqual(h, value / axis_max * PLOT_HEIGHT, delta=0.02, msg=b.get("data-label"))
            self.assertAlmostEqual(y + h, BASELINE, delta=0.02, msg="every bar must start at the zero baseline")

    def test_axis_runs_from_zero_to_nice_max(self):
        ticks = [t.text for t in self.find("text", "tick")]
        self.assertEqual(ticks, ["0", "10,000", "20,000", "30,000", "40,000", "50,000"])
        base = self.find("line", "baseline")
        self.assertEqual(len(base), 1)
        self.assertAlmostEqual(float(base[0].get("y1")), BASELINE, delta=0.01)

    def test_bars_are_labelled(self):
        want = sorted(self.rows, key=lambda r: (-r[1], r[0]))
        self.assertEqual([t.text for t in self.find("text", "bar-label")], [r[0] for r in want])
        self.assertEqual([t.text for t in self.find("text", "value-label")], ["{:,}".format(r[1]) for r in want])

    def test_small_values(self):
        _, find = parse(chart.bar_chart_svg([("A", 0.8), ("B", 3)], "Small"))
        heights = {b.get("data-label"): float(b.get("height")) for b in find("rect", "bar")}
        self.assertAlmostEqual(heights["B"], 3 / 5 * PLOT_HEIGHT, delta=0.02)
        self.assertAlmostEqual(heights["A"], 0.8 / 5 * PLOT_HEIGHT, delta=0.02)

    def test_rejects_negative_and_empty(self):
        with self.assertRaises(ValueError):
            chart.bar_chart_svg([("A", 5), ("B", -2)], "Bad")
        with self.assertRaises(ValueError):
            chart.bar_chart_svg([], "Empty")


if __name__ == "__main__":
    unittest.main()
