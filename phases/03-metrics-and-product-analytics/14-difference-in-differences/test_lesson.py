"""Tests for lesson 14: difference in differences. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Every expected number is computed here independently: cell means with SQLite GROUP BY,
the regression checked through its normal equations (each residual column sums to 0),
the slope with the n Sxy formula. The tests run on the committed data and on a second
dataset built with another seed."""
import csv
import importlib.util
import os
import sqlite3
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "zone_weeks.csv")
OTHER_SEED = 5
LAUNCH = 9
ALL_CONTROLS = ["Nashik", "Indore", "Nagpur"]
CLEAN = ["Nashik", "Indore"]
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")


def load_module():
    spec = importlib.util.spec_from_file_location("lesson_module", TARGET)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load_module()
sys.path.insert(0, HERE)
import make_data  # noqa: E402


def as_rows(text_rows):
    return [{"city": r["city"], "zone": r["zone"], "week": int(r["week"]), "orders": float(r["orders"])}
            for r in text_rows]


def sql_means(rows, treated, controls, launch):
    """Independent route: the four cell means with SQLite."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE z (city TEXT, week INTEGER, orders REAL)")
    con.executemany("INSERT INTO z VALUES (?, ?, ?)", [(r["city"], r["week"], r["orders"]) for r in rows])
    marks = ",".join("?" * len(controls))
    q = ("SELECT city = ? AS t, week >= ? AS p, AVG(orders) FROM z WHERE city = ? OR city IN (%s) "
         "GROUP BY t, p" % marks)
    out = {(int(t), int(p)): v for t, p, v in con.execute(q, [treated, launch, treated] + list(controls))}
    con.close()
    return out


def sql_did(rows, treated, controls, launch):
    c = sql_means(rows, treated, controls, launch)
    return (c[(1, 1)] - c[(1, 0)]) - (c[(0, 1)] - c[(0, 0)])


def read_committed():
    with open(DATA, newline="") as f:
        return as_rows(list(csv.DictReader(f)))


def ref_slope(xs, ys):
    n = len(xs)
    return (n * sum(x * y for x, y in zip(xs, ys)) - sum(xs) * sum(ys)) / (n * sum(x * x for x in xs) - sum(xs) ** 2)


def ref_pre_slope(rows, treated, controls, launch):
    weeks = sorted({r["week"] for r in rows if r["week"] < launch})
    gaps = []
    for w in weeks:
        t = [r["orders"] for r in rows if r["week"] == w and r["city"] == treated]
        c = [r["orders"] for r in rows if r["week"] == w and r["city"] in controls]
        gaps.append(sum(t) / len(t) - sum(c) / len(c))
    return ref_slope(weeks, gaps)


def tiny():
    """Treated before 10 and 12, treated after 20, control before 5, control after 8, plus a city to ignore."""
    data = [("T", 1, 10), ("T", 1, 12), ("T", 2, 20), ("C", 1, 5), ("C", 2, 8), ("X", 1, 999), ("X", 2, 0)]
    return [{"city": c, "zone": c, "week": w, "orders": float(y)} for c, w, y in data]


class TestSmallCases(unittest.TestCase):
    def test_cell_means_and_did(self):
        means = m.cell_means(tiny(), "T", ["C"], 2)
        self.assertEqual(means, {(1, 0): 11.0, (1, 1): 20.0, (0, 0): 5.0, (0, 1): 8.0},
                         "cell means are keyed (treated, post); city X is in neither group and is ignored")
        self.assertAlmostEqual(m.did_from_means(means), 6.0, msg="(20 - 11) - (8 - 5) = 6")

    def test_empty_cell(self):
        rows = [r for r in tiny() if not (r["city"] == "C" and r["week"] == 2)]
        means = m.cell_means(rows, "T", ["C"], 2)
        self.assertIsNone(means[(0, 1)], "no control rows after launch: that cell is None, not 0")
        self.assertIsNone(m.did_from_means(means), "a DiD with an empty cell cannot be computed")
        with self.assertRaises(ValueError, msg="with no control-after rows, P and T x P are the same column"):
            m.did_regression(rows, "T", ["C"], 2)

    def test_ols(self):
        b = m.ols([[1.0, 0.0], [1.0, 1.0], [1.0, 2.0]], [1.0, 3.0, 5.0])
        self.assertAlmostEqual(b[0], 1.0)
        self.assertAlmostEqual(b[1], 2.0, msg="y = 1 + 2x exactly: the slope coefficient is 2")
        b = m.ols([[1.0, 0.0], [1.0, 1.0], [1.0, 1.0], [1.0, 0.0]], [0.0, 1.0, 3.0, 2.0])
        self.assertAlmostEqual(b[1], 1.0, msg="least squares through two points per x: (1 + 3)/2 - (0 + 2)/2 = 1")
        with self.assertRaises(ValueError):
            m.ols([[1.0, 2.0], [2.0, 4.0]], [1.0, 2.0])
        with self.assertRaises(ValueError):
            m.ols([], [])

    def test_regression_on_unbalanced_cells(self):
        reg = m.did_regression(tiny(), "T", ["C"], 2)
        self.assertAlmostEqual(reg["did"], 6.0, msg="the interaction coefficient equals the DiD of cell means, "
                                                    "even when cells have different numbers of rows")
        self.assertAlmostEqual(reg["intercept"], 5.0, msg="the intercept is the control-before mean")
        self.assertAlmostEqual(reg["treated"], 6.0)
        self.assertAlmostEqual(reg["post"], 3.0)

    def test_slope(self):
        self.assertIsNone(m.slope([1], [5.0]), "one point has no slope")
        self.assertIsNone(m.slope([2, 2], [1.0, 3.0]), "all x equal: no slope")
        self.assertAlmostEqual(m.slope([1, 2, 3], [4.0, 4.0, 4.0]), 0.0)
        self.assertAlmostEqual(m.slope([1, 2, 3, 4], [1.0, 3.0, 2.0, 5.0]), 1.1)

    def test_parallel_and_diverging(self):
        rows = []
        for w in range(1, 5):
            rows.append({"city": "T", "zone": "t", "week": w, "orders": 50.0 + 2 * w})
            rows.append({"city": "C", "zone": "c", "week": w, "orders": 20.0 + 2 * w})
            rows.append({"city": "D", "zone": "d", "week": w, "orders": 20.0 + 5 * w})
        self.assertEqual(m.pre_gaps(rows, "T", ["C"], 4), {1: 30.0, 2: 30.0, 3: 30.0},
                         "gaps are for weeks before launch only (week 4 is the launch week)")
        self.assertAlmostEqual(m.pre_trend_slope(rows, "T", ["C"], 4), 0.0, msg="parallel lines: slope 0")
        self.assertAlmostEqual(m.pre_trend_slope(rows, "T", ["D"], 4), -3.0,
                               msg="the control grows 3 a week faster, so the gap shrinks by 3 a week")
        self.assertIsNone(m.pre_trend_slope(rows, "T", ["C"], 2), "one pre-launch week cannot show a trend")


class OnDataMixin:
    rows = None

    def test_did_two_routes(self):
        for controls in (ALL_CONTROLS, CLEAN):
            want = sql_did(self.rows, "Pune", controls, LAUNCH)
            got = m.did_from_means(m.cell_means(self.rows, "Pune", controls, LAUNCH))
            self.assertAlmostEqual(got, want, places=9, msg="DiD by means with %s: expected %.3f" % (controls, want))
            reg = m.did_regression(self.rows, "Pune", controls, LAUNCH)
            self.assertAlmostEqual(reg["did"], want, places=6,
                                   msg="the interaction coefficient must equal the DiD of means (%.3f)" % want)

    def test_regression_normal_equations(self):
        reg = m.did_regression(self.rows, "Pune", CLEAN, LAUNCH)
        b = [reg["intercept"], reg["treated"], reg["post"], reg["did"]]
        sums = [0.0] * 4
        for r in self.rows:
            if r["city"] != "Pune" and r["city"] not in CLEAN:
                continue
            t, p = float(r["city"] == "Pune"), float(r["week"] >= LAUNCH)
            x = [1.0, t, p, t * p]
            e = r["orders"] - sum(xi * bi for xi, bi in zip(x, b))
            sums = [s + e * xi for s, xi in zip(sums, x)]
        for name, s in zip(("intercept", "treated", "post", "did"), sums):
            self.assertAlmostEqual(s, 0.0, places=5, msg="least squares: residuals times the %s column "
                                                         "must sum to 0" % name)

    def test_pre_trend(self):
        for controls in (ALL_CONTROLS, CLEAN, ["Nagpur"]):
            want = ref_pre_slope(self.rows, "Pune", controls, LAUNCH)
            self.assertAlmostEqual(m.pre_trend_slope(self.rows, "Pune", controls, LAUNCH), want, places=9,
                                   msg="pre-trend slope vs %s: expected %.3f" % (controls, want))

    def test_placebo_in_time(self):
        pre = [r for r in self.rows if r["week"] < LAUNCH]
        want = sql_did(pre, "Pune", CLEAN, 5)
        self.assertAlmostEqual(m.did_from_means(m.cell_means(pre, "Pune", CLEAN, 5)), want, places=9)

    def test_story(self):
        self.assertLess(abs(ref_pre_slope(self.rows, "Pune", CLEAN, LAUNCH)), 1.0)
        self.assertLess(ref_pre_slope(self.rows, "Pune", ["Nagpur"], LAUNCH), -1.5)
        self.assertGreater(sql_did(self.rows, "Pune", CLEAN, LAUNCH), sql_did(self.rows, "Pune", ALL_CONTROLS, LAUNCH))


class TestOnData(OnDataMixin, unittest.TestCase):
    rows = read_committed()


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""
    rows = as_rows(make_data.build(seed=OTHER_SEED))


if __name__ == "__main__":
    unittest.main()
