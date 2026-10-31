"""Tests for lesson 04: draw a chart from scratch.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

Expected values (the axis maximum, bar heights, order, labels) are computed
here independently. The chart checks run on the committed CSV, on a second
dataset built in memory with another seed (a different axis maximum), and
on small hand-made inputs: a tie, all zeros, one bar, quotes in a label.
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
SECOND_SEED = 4173  # largest value 23,300, so the axis tops out at 25,000, not 50,000


def read_rows():
    with open(os.path.join(HERE, "data", "product_line_revenue.csv"), newline="") as f:
        return [(r["product_line"], int(r["revenue"])) for r in csv.DictReader(f)]


def rows_from_build(seed):
    spec_ = importlib.util.spec_from_file_location("make_data", os.path.join(HERE, "make_data.py"))
    module = importlib.util.module_from_spec(spec_)
    spec_.loader.exec_module(module)
    return [(r["product_line"], int(r["revenue"])) for r in module.build(seed=seed)["product_line_revenue"]]


def reference_nice_max(value):
    """Independent version: try every m * 10**k from small to large."""
    if value <= 0:
        return 1
    for k in range(-6, 13):
        for m in (1, 2, 2.5, 5):
            candidate = m * 10 ** k
            if candidate >= value - 1e-12:
                return candidate
    raise ValueError(value)


def parse(svg):
    root = ET.fromstring(svg)

    def find(tag, cls):
        return [e for e in root.iter(NS + tag) if e.get("class") == cls]
    return root, find


class TestHelpers(unittest.TestCase):
    def test_nice_max(self):
        cases = {7: 10, 42: 50, 1234: 2000, 200: 200, 0.3: 0.5, 18.5: 20, 23: 25, 1: 1, 38900: 50000, 0: 1, -5: 1}
        for value, want in cases.items():
            self.assertAlmostEqual(chart.nice_max(value), want, msg="nice_max(%r) should be %r" % (value, want))
        for value in (0.07, 3, 99, 101, 2500.5, 23300, 480000):
            self.assertAlmostEqual(chart.nice_max(value), reference_nice_max(value), msg="nice_max(%r)" % value)

    def test_axis_ticks(self):
        self.assertEqual([float(t) for t in chart.axis_ticks(50000)], [0, 10000, 20000, 30000, 40000, 50000])
        for got, want in zip(chart.axis_ticks(2.5), [0, 0.5, 1, 1.5, 2, 2.5]):
            self.assertAlmostEqual(got, want)
        self.assertEqual(len(chart.axis_ticks(1)), 6, "five steps give six ticks, zero included")

    def test_sort_rows(self):
        rows = [("B", 5), ("A", 5), ("C", 9), ("D", 1)]
        self.assertEqual(chart.sort_rows(rows), [("C", 9), ("A", 5), ("B", 5), ("D", 1)],
                         "largest first, and a tie is broken by label A to Z")
        self.assertEqual(chart.sort_rows([]), [], "an empty list sorts to an empty list")
        self.assertEqual(chart.sort_rows([("Z", 0), ("A", 0)]), [("A", 0), ("Z", 0)], "zeros tie too")


class TestChooseChart(unittest.TestCase):
    def test_clear_cases(self):
        self.assertEqual(chart.choose_chart("compare"), "bar")
        self.assertEqual(chart.choose_chart("rank"), "bar")
        self.assertEqual(chart.choose_chart("distribution"), "histogram")
        self.assertEqual(chart.choose_chart("relationship"), "scatter")
        self.assertEqual(chart.choose_chart("trend", 12), "line")

    def test_boundaries_and_ambiguous_cases(self):
        self.assertEqual(chart.choose_chart("trend", 4), "bar", "four quarters: separate totals read well as bars")
        self.assertEqual(chart.choose_chart("trend", 5), "line", "five periods or more: a line")
        self.assertEqual(chart.choose_chart("part_to_whole", 2), "stacked bar")
        self.assertEqual(chart.choose_chart("part_to_whole", 4), "stacked bar")
        self.assertEqual(chart.choose_chart("part_to_whole", 5), "bar", "five or more parts: a sorted bar, not slices")
        self.assertEqual(chart.choose_chart("compare", 40), "bar", "n_items does not change a comparison")
        self.assertEqual(chart.choose_chart("distribution", 3), "histogram", "n_items does not change a distribution")

    def test_refuses_what_it_does_not_cover(self):
        for bad in ("3d pie", "Trend", "", None):
            with self.assertRaises(ValueError, msg="choose_chart(%r) should raise ValueError" % (bad,)):
                chart.choose_chart(bad)
        for task in ("trend", "part_to_whole"):
            for n in (None, 0, 1, 2.5, "12"):
                with self.assertRaises(ValueError, msg="choose_chart(%r, %r) should raise ValueError" % (task, n)):
                    chart.choose_chart(task, n)


class ChartChecks:
    rows = None
    title = "Revenue by product line"

    @classmethod
    def setUpClass(cls):
        cls.svg = chart.bar_chart_svg(cls.rows, cls.title)
        cls.root, find = parse(cls.svg)
        cls.find = staticmethod(find)
        cls.want = sorted(cls.rows, key=lambda r: (-r[1], r[0]))
        cls.axis_max = reference_nice_max(max(v for _, v in cls.rows))

    def test_is_valid_svg_with_title(self):
        self.assertEqual(self.root.tag, NS + "svg")
        self.assertEqual([t.text for t in self.find("text", "title")], [self.title])

    def test_one_bar_per_row_sorted_largest_first(self):
        bars = self.find("rect", "bar")
        self.assertEqual([b.get("data-label") for b in bars], [r[0] for r in self.want],
                         "one bar per row, largest first, ties A to Z")
        xs = [float(b.get("x")) for b in bars]
        self.assertEqual(xs, sorted(xs), "bars must run left to right in sorted order")

    def test_data_value_is_the_input_value(self):
        got = [float(b.get("data-value")) for b in self.find("rect", "bar")]
        self.assertEqual(got, [float(v) for _, v in self.want], "data-value must be each row's value, in bar order")

    def test_bar_heights_scale_from_zero(self):
        for b, (label, value) in zip(self.find("rect", "bar"), self.want):
            h, y = float(b.get("height")), float(b.get("y"))
            self.assertAlmostEqual(h, value / self.axis_max * PLOT_HEIGHT, delta=0.02,
                                   msg="%s: height should be value / %s * 300" % (label, self.axis_max))
            self.assertAlmostEqual(y + h, BASELINE, delta=0.02, msg="every bar must start at the zero baseline")

    def test_axis_runs_from_zero_to_nice_max(self):
        want = [chart.fmt(self.axis_max * i / 5) for i in range(6)]
        self.assertEqual([t.text for t in self.find("text", "tick")], want)
        base = self.find("line", "baseline")
        self.assertEqual(len(base), 1)
        self.assertAlmostEqual(float(base[0].get("y1")), BASELINE, delta=0.01)

    def test_bars_are_labelled(self):
        self.assertEqual([t.text for t in self.find("text", "bar-label")], [r[0] for r in self.want])
        self.assertEqual([t.text for t in self.find("text", "value-label")], [chart.fmt(r[1]) for r in self.want])


class TestCommittedData(ChartChecks, unittest.TestCase):
    rows = read_rows()

    def test_axis_is_fifty_thousand(self):
        self.assertEqual(max(v for _, v in self.rows), 38900)
        self.assertEqual(self.axis_max, 50000)


class TestSecondDataset(ChartChecks, unittest.TestCase):
    """Another seed: the axis is 25,000, so a hard-coded 50,000 fails."""
    rows = rows_from_build(SECOND_SEED)


class TestTieAndQuotes(ChartChecks, unittest.TestCase):
    """A tie, a value of zero, and a label with a double quote and an ampersand."""
    rows = [('The "Pro" line', 30), ("B & C", 30), ("Zero", 0), ("Ace", 12.5)]
    title = 'Revenue & "units"'


class TestSingleBar(ChartChecks, unittest.TestCase):
    rows = [("Only", 0.8)]


class TestEdgeCases(unittest.TestCase):
    def test_small_values(self):
        _, find = parse(chart.bar_chart_svg([("A", 0.8), ("B", 3)], "Small"))
        heights = {b.get("data-label"): float(b.get("height")) for b in find("rect", "bar")}
        self.assertAlmostEqual(heights["B"], 3 / 5 * PLOT_HEIGHT, delta=0.02)
        self.assertAlmostEqual(heights["A"], 0.8 / 5 * PLOT_HEIGHT, delta=0.02)

    def test_all_zero_values_draw_flat_bars(self):
        _, find = parse(chart.bar_chart_svg([("A", 0), ("B", 0)], "Nothing yet"))
        self.assertEqual([float(b.get("height")) for b in find("rect", "bar")], [0.0, 0.0],
                         "zero values are bars of height 0 on an axis from 0 to 1, not an error")

    def test_rejects_negative_and_empty(self):
        with self.assertRaises(ValueError):
            chart.bar_chart_svg([("A", 5), ("B", -2)], "Bad")
        with self.assertRaises(ValueError):
            chart.bar_chart_svg([], "Empty")


if __name__ == "__main__":
    unittest.main()
