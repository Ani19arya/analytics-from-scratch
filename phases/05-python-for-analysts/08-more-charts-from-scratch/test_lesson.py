"""Tests for lesson 08: more charts from scratch.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

Expected bins, counts, peaks, axis ranges and pixel positions are computed here in plain
Python, never by calling the lesson's own functions. The SVG is parsed as XML and every
bar, point and line vertex is checked. The checks run on the committed CSV, on a second
dataset from make_data.build(seed=2038) in memory, and on small hand-made inputs: no values,
one value, a value on a bin edge, a plateau, all zeros and an ampersand in a title.
"""
import csv
import importlib.util
import math
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
OTHER_SEED = 2038
NS = "{http://www.w3.org/2000/svg}"
LEFT, TOP, PLOT_WIDTH, PLOT_HEIGHT, BASELINE = 60, 40, 520, 300, 340


def typed(rows):
    return [{"order_date": date.fromisoformat(r["order_date"]), "distance_km": float(r["distance_km"]),
             "minutes": float(r["minutes"])} for r in rows]


def read_committed():
    with open(os.path.join(HERE, "data", "deliveries.csv"), newline="") as f:
        return typed(list(csv.DictReader(f)))


# ---- independent reference versions ---------------------------------------------

def ref_counts(values, width):
    """Bins by counting comparisons, no index arithmetic."""
    start = math.floor(min(values) / width) * width
    edges = [start]
    while edges[-1] <= max(values):
        edges.append(edges[-1] + width)
    counts = [sum(1 for v in values if edges[i] <= v < edges[i + 1]) for i in range(len(edges) - 1)]
    return edges, counts


def ref_peaks(counts):
    n = 0
    for i, c in enumerate(counts):
        left = next((counts[j] for j in range(i - 1, -1, -1) if counts[j] != c), 0)
        right = next((counts[j] for j in range(i + 1, len(counts)) if counts[j] != c), 0)
        first_of_run = i == 0 or counts[i - 1] != c
        if first_of_run and c > left and c > right:
            n += 1
    return n


def ref_nice(v):
    if v <= 0:
        return 1
    for k in range(-6, 13):
        for m in (1, 2, 2.5, 5):
            if m * 10 ** k >= v - 1e-12:
                return m * 10 ** k


def ref_zoom(values):
    lo, hi = min(values), max(values)
    step = ref_nice((hi - lo) / 8) if hi > lo else (ref_nice(abs(hi)) or 1)
    a, b = math.floor(lo / step) * step, math.ceil(hi / step) * step
    return (a, b) if b > a else (a - step, b + step)


def ref_daily(rows):
    if not rows:
        return []
    first = min(r["order_date"] for r in rows)
    last = max(r["order_date"] for r in rows)
    return [sum(1 for r in rows if r["order_date"] == first + timedelta(days=i))
            for i in range((last - first).days + 1)]


def parse(svg):
    root = ET.fromstring(svg)
    return lambda tag, cls: [e for e in root.iter(NS + tag) if e.get("class") == cls]


class TestBins(unittest.TestCase):
    def test_bin_edges(self):
        self.assertEqual(list(lesson.bin_edges([0, 10], 5)), [0, 5, 10, 15],
                         "the maximum 10 must sit inside a bin, so the last edge is 15, not 10")
        self.assertEqual(list(lesson.bin_edges([3], 5)), [0, 5], "one value still gets one bin")
        self.assertEqual(list(lesson.bin_edges([-3, 4], 5)), [-5, 0, 5], "start rounds DOWN, also below zero")
        self.assertEqual(list(lesson.bin_edges([7, 12], 5, start=2.5)), [2.5, 7.5, 12.5])
        self.assertEqual(list(lesson.bin_edges([], 5)), [])
        for bad in (0, -1):
            with self.assertRaises(ValueError, msg="a bin width of %s must raise ValueError" % bad):
                lesson.bin_edges([1, 2], bad)

    def test_histogram_small(self):
        edges, counts = lesson.histogram([20.0, 24.9, 25.0, 0.0], 5)
        self.assertEqual((list(edges), list(counts)), ([0, 5, 10, 15, 20, 25, 30], [1, 0, 0, 0, 2, 1]),
                         "bins are edges[i] <= v < edges[i+1]: 25.0 goes in the 25 to 30 bin, and empty bins stay as 0")
        self.assertEqual(tuple(map(list, lesson.histogram([], 5))), ([], []))
        with self.assertRaises(ValueError, msg="a value below start must raise, not vanish from the counts"):
            lesson.histogram([1, 9], 5, start=5)

    def test_count_peaks(self):
        cases = [([], 0), ([0, 0], 0), ([2], 1), ([1, 3, 3, 1], 1), ([5, 1, 5], 2), ([1, 2, 3], 1),
                 ([3, 3, 1, 3, 3], 2), ([1, 4, 2, 4, 1], 2), ([0, 2, 2, 3, 2, 2, 0], 1)]
        for counts, want in cases:
            self.assertEqual(lesson.count_peaks(counts), want, "count_peaks(%r) should be %d" % (counts, want))


class TestScales(unittest.TestCase):
    def test_linear_scale(self):
        y = lesson.linear_scale(0, 50, BASELINE, TOP)
        self.assertAlmostEqual(y(0), BASELINE)
        self.assertAlmostEqual(y(50), TOP)
        self.assertAlmostEqual(y(25), 190, msg="halfway up the axis is halfway between 340 and 40")
        self.assertAlmostEqual(lesson.linear_scale(10, 20, 0, 100)(5), -50, msg="the scale is a straight line, "
                               "also outside the domain")
        with self.assertRaises(ValueError):
            lesson.linear_scale(3, 3, 0, 100)

    def test_value_domain(self):
        self.assertEqual(tuple(lesson.value_domain([3, 7], "histogram")), (0, 10))
        self.assertEqual(tuple(lesson.value_domain([269, 112], "bar")), (0, 500),
                         "bars and histograms start at 0: their length is the value")
        self.assertEqual(tuple(lesson.value_domain([0, 0], "histogram")), (0, 1))
        self.assertEqual(tuple(lesson.value_domain([25, 46], "line")), (25, 50), "a line may zoom: 25 to 50 in steps of 5")
        self.assertEqual(tuple(lesson.value_domain([0.6, 9.5], "scatter")), (0, 10))
        self.assertEqual(tuple(lesson.value_domain([5, 5], "line")), (0, 10), "one repeated value still needs a range")
        for values in ([32, 25, 46, 44], [-7, 3], [101, 180], [0.6, 0.6]):
            lo, hi = lesson.value_domain(values, "line")
            want = ref_zoom(values)
            self.assertAlmostEqual(lo, want[0], msg="value_domain(%r, 'line') low end" % values)
            self.assertAlmostEqual(hi, want[1], msg="value_domain(%r, 'line') high end" % values)
        with self.assertRaises(ValueError):
            lesson.value_domain([1, 2], "pie")


class TestSvgSmall(unittest.TestCase):
    def test_histogram_svg_all_zero_and_escaping(self):
        find = parse(lesson.histogram_svg([0, 5, 10], [0, 0], "Tea & snacks"))
        bars = find("rect", "bar")
        self.assertEqual(len(bars), 2, "one rect per bin, even when it is empty")
        for b in bars:
            self.assertAlmostEqual(float(b.get("height")), 0.0, places=2)
            self.assertAlmostEqual(float(b.get("y")), BASELINE, places=2)

    def test_scatter_lengths(self):
        with self.assertRaises(ValueError):
            lesson.scatter_svg([1, 2], [1], "bad")

    def test_line_one_value_and_labels(self):
        find = parse(lesson.line_svg([7], "One day", ["Mon"]))
        pts = find("polyline", "line")[0].get("points").split()
        self.assertEqual(len(pts), 1)
        self.assertAlmostEqual(float(pts[0].split(",")[0]), LEFT + PLOT_WIDTH / 2, places=1,
                               msg="a single point sits in the middle of the plot")
        self.assertEqual([t.text for t in find("text", "xtick")], ["Mon"])
        with self.assertRaises(ValueError):
            lesson.line_svg([1, 2, 3], "t", ["a", "b"])
        with self.assertRaises(ValueError):
            lesson.line_svg([], "t")

    def test_daily_counts_fills_gaps(self):
        rows = [{"order_date": date(2026, 10, 3)}, {"order_date": date(2026, 10, 1)}, {"order_date": date(2026, 10, 3)}]
        self.assertEqual(list(lesson.daily_counts(rows)), [1, 0, 2],
                         "a day with no deliveries is a 0 on the chart, not a missing point")
        self.assertEqual(list(lesson.daily_counts([])), [])


class DataChecks:
    rows = None

    def test_histograms_and_peaks(self):
        minutes = [r["minutes"] for r in self.rows]
        for width in (20, 10, 5):
            edges, counts = lesson.histogram(minutes, width)
            want_edges, want_counts = ref_counts(minutes, width)
            self.assertEqual(list(counts), want_counts, "counts for %d-minute bins" % width)
            for got, want in zip(edges, want_edges):
                self.assertAlmostEqual(got, want)
            self.assertEqual(sum(counts), len(minutes), "every delivery lands in exactly one bin")
            self.assertEqual(lesson.count_peaks(counts), ref_peaks(want_counts), "peaks for %d-minute bins" % width)

    def test_histogram_svg_bars(self):
        minutes = [r["minutes"] for r in self.rows]
        edges, counts = ref_counts(minutes, 5)
        find = parse(lesson.histogram_svg(edges, counts, "Delivery time, 5-minute bins"))
        bars = find("rect", "bar")
        self.assertEqual(len(bars), len(counts))
        top = ref_nice(max(counts))
        x_step = PLOT_WIDTH / len(counts)
        for i, (b, c) in enumerate(zip(bars, counts)):
            x, y, w, h = (float(b.get(k)) for k in ("x", "y", "width", "height"))
            self.assertAlmostEqual(h, c / top * PLOT_HEIGHT, places=1,
                                   msg="bar %d: height should be count / %s * 300, on an axis from 0" % (i, top))
            self.assertAlmostEqual(y + h, BASELINE, places=1, msg="bar %d must stand on the baseline" % i)
            self.assertAlmostEqual(x, LEFT + i * x_step, places=1, msg="bars touch: bar %d starts where the last ended" % i)
            self.assertAlmostEqual(w, x_step, places=1)
        self.assertEqual(len(find("text", "xtick")), len(edges), "one x label under every edge")

    def test_scatter_points(self):
        xs, ys = [r["distance_km"] for r in self.rows], [r["minutes"] for r in self.rows]
        find = parse(lesson.scatter_svg(xs, ys, "Distance and delivery time"))
        points = find("circle", "point")
        self.assertEqual(len(points), len(xs), "one circle per delivery")
        (x0, x1), (y0, y1) = ref_zoom(xs), ref_zoom(ys)
        for p, a, b in list(zip(points, xs, ys))[::37]:
            self.assertAlmostEqual(float(p.get("cx")), LEFT + (a - x0) / (x1 - x0) * PLOT_WIDTH, places=1)
            self.assertAlmostEqual(float(p.get("cy")), BASELINE - (b - y0) / (y1 - y0) * PLOT_HEIGHT, places=1,
                                   msg="cy is BASELINE minus the share of the axis, scaled to 300 pixels")

    def test_daily_line(self):
        want = ref_daily(self.rows)
        got = list(lesson.daily_counts(self.rows))
        self.assertEqual(got, want, "deliveries per day, first day to last")
        find = parse(lesson.line_svg(got, "Deliveries per day"))
        pts = [tuple(map(float, p.split(","))) for p in find("polyline", "line")[0].get("points").split()]
        self.assertEqual(len(pts), len(want))
        lo, hi = ref_zoom(want)
        for i, ((px, py), v) in enumerate(zip(pts, want)):
            self.assertAlmostEqual(px, LEFT + i * PLOT_WIDTH / (len(want) - 1), places=1)
            self.assertAlmostEqual(py, BASELINE - (v - lo) / (hi - lo) * PLOT_HEIGHT, places=1,
                                   msg="day %d: y on the zoomed %s to %s axis" % (i, lo, hi))


class TestCommittedData(DataChecks, unittest.TestCase):
    rows = read_committed()


class TestSecondData(DataChecks, unittest.TestCase):
    rows = typed(make_data.build(OTHER_SEED)["deliveries"])


if __name__ == "__main__":
    unittest.main()
