"""Tests for lesson 09. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Expected answers are computed here, never read from the solution file:
- chi2_sf is checked against closed forms that need only math.erfc and
  math.exp (df = 1, 2, 3, 4 and 6), and against printed chi-square table values
  (the 5% and 1% critical values, given to 3 decimals);
- for a 2 x 2 table the chi-square statistic must equal z squared from the
  pooled two-proportion z-test (lesson 03), a different formula;
- the expected counts and the statistic are written out again below.
Everything runs on the committed data AND on a second dataset built in memory
from make_data.build(seed=OTHER_SEED)."""
import ast
import csv
import importlib.util
import math
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "signups.csv")
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")
BANNED = {"statistics", "numpy", "pandas", "scipy", "statsmodels"}
OTHER_SEED = 19

CLOSED_FORMS = {
    1: lambda x: math.erfc(math.sqrt(x / 2)),
    2: lambda x: math.exp(-x / 2),
    3: lambda x: math.erfc(math.sqrt(x / 2)) + math.sqrt(2 * x / math.pi) * math.exp(-x / 2),
    4: lambda x: math.exp(-x / 2) * (1 + x / 2),
    6: lambda x: math.exp(-x / 2) * (1 + x / 2 + (x / 2) ** 2 / 2),
}
# (critical value, df, upper tail) from a standard chi-square table.
TABLE = [(3.841, 1, 0.05), (5.991, 2, 0.05), (7.815, 3, 0.05), (9.488, 4, 0.05), (11.070, 5, 0.05),
         (18.307, 10, 0.05), (31.410, 20, 0.05), (124.342, 100, 0.05),
         (6.635, 1, 0.01), (9.210, 2, 0.01), (11.345, 3, 0.01), (13.277, 4, 0.01), (23.209, 10, 0.01)]


def load():
    spec = importlib.util.spec_from_file_location("lesson_module", TARGET)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def imported_modules(path):
    with open(path) as f:
        tree = ast.parse(f.read())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def table_of(path):
    counts = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r["completed"] == "":
                continue
            counts.setdefault(r["flow"], [0, 0])[0 if r["completed"] == "1" else 1] += 1
    flows = sorted(counts)
    return flows, [counts[k] for k in flows]


def ref_test(obs):
    n = sum(map(sum, obs))
    rows = [sum(r) for r in obs]
    cols = [sum(obs[i][j] for i in range(len(obs))) for j in range(len(obs[0]))]
    exp = [[rows[i] * cols[j] / n for j in range(len(cols))] for i in range(len(rows))]
    chi2 = 0.0
    for i in range(len(rows)):
        for j in range(len(cols)):
            chi2 += (obs[i][j] - exp[i][j]) ** 2 / exp[i][j]
    df = (len(rows) - 1) * (len(cols) - 1)
    v = math.sqrt(chi2 / (n * (min(len(rows), len(cols)) - 1)))
    return exp, chi2, df, v


def z_squared(ca, na, cb, nb):
    pool = (ca + cb) / (na + nb)
    se = math.sqrt(pool * (1 - pool) * (1 / na + 1 / nb))
    return ((cb / nb - ca / na) / se) ** 2


m = load()


class TestRules(unittest.TestCase):
    def test_no_statistics_library(self):
        used = imported_modules(TARGET) & BANNED
        self.assertFalse(used, "Write the test yourself: remove the import of %s." % ", ".join(sorted(used)))


class TestChi2Sf(unittest.TestCase):
    def test_closed_forms(self):
        for df, f in CLOSED_FORMS.items():
            for x in (0.01, 0.5, 1.0, 2.0, 2.9, 3.0, 3.1, 4.0, 7.5, 10.0, 25.0, 60.0):
                want = f(x)
                got = m.chi2_sf(x, df)
                self.assertLess(abs(got - want), 1e-10 * max(want, 1e-12) + 1e-14,
                                "chi2_sf(%s, %d) should be %.12g, got %.12g; check the series and the continued fraction"
                                % (x, df, want, got))

    def test_table_values(self):
        for x, df, tail in TABLE:
            self.assertAlmostEqual(m.chi2_sf(x, df), tail, delta=tail * 0.003,
                                   msg="a chi-square table gives P(X >= %.3f) = %s for %d degrees of freedom" % (x, tail, df))

    def test_edges(self):
        self.assertEqual(m.chi2_sf(0, 2), 1.0, "a statistic of 0 has upper tail 1")
        self.assertLess(m.chi2_sf(400, 2), 1e-80)
        self.assertGreater(m.chi2_sf(400, 2), 0.0, "very small, but not 0: exp(-200)")
        with self.assertRaises(ValueError):
            m.chi2_sf(1.0, 0)


class TestPieces(unittest.TestCase):
    def test_expected_counts(self):
        obs = [[10, 20], [30, 40]]
        exp = m.expected_counts(obs)
        want = ref_test(obs)[0]
        for i in range(2):
            for j in range(2):
                self.assertAlmostEqual(exp[i][j], want[i][j], places=9,
                                       msg="expected = row total * column total / grand total")

    def test_statistic_and_df(self):
        obs = [[12, 8], [5, 15], [9, 11]]
        exp = m.expected_counts(obs)
        self.assertAlmostEqual(m.chi_square_statistic(obs, exp), ref_test(obs)[1], places=9)
        self.assertEqual(m.degrees_of_freedom(3, 2), 2, "(rows - 1) * (columns - 1)")
        self.assertEqual(m.degrees_of_freedom(4, 5), 12)

    def test_cramers_v(self):
        self.assertAlmostEqual(m.cramers_v(10.0, 1000, 3, 2), math.sqrt(10.0 / 1000), places=12,
                               msg="V = sqrt(chi2 / (n * (min(rows, cols) - 1)))")
        self.assertAlmostEqual(m.cramers_v(30.0, 500, 4, 3), math.sqrt(30.0 / (500 * 2)), places=12)

    def test_two_by_two_equals_z_squared(self):
        r = m.chi_square_test([[200, 1800], [260, 1740]])
        self.assertAlmostEqual(r["chi2"], z_squared(200, 2000, 260, 2000), places=9,
                               msg="for 2 x 2 the chi-square is z squared from the two-proportion test, with no Yates correction")
        self.assertAlmostEqual(r["p_value"], math.erfc(math.sqrt(r["chi2"] / 2)), places=12)


class TestTest(unittest.TestCase):
    def test_identical_rows(self):
        r = m.chi_square_test([[30, 70], [30, 70], [60, 140]])
        self.assertAlmostEqual(r["chi2"], 0.0, places=12)
        self.assertAlmostEqual(r["p_value"], 1.0, places=12, msg="identical rates: no evidence, p = 1")
        self.assertEqual(r["small_cells"], [])

    def test_small_expected_counts_are_flagged(self):
        r = m.chi_square_test([[3, 9], [1, 11], [6, 4]])
        exp = ref_test([[3, 9], [1, 11], [6, 4]])[0]
        want = [(i, j) for i in range(3) for j in range(2) if exp[i][j] < 5]
        self.assertEqual(r["small_cells"], want,
                         "list every (row, column) whose EXPECTED count is below 5, in row order")

    def test_bad_tables(self):
        bad = [[], [[5, 5]], [[5], [5]], [[0, 0], [3, 4]], [[0, 5], [0, 7]], [[1, 2], [3]],
               [[55.5, 44.5], [62.7, 37.3]]]
        for table in bad:
            with self.assertRaises(ValueError, msg="should refuse %r" % (table,)):
                m.chi_square_test(table)

    def test_counts_matter_not_just_rates(self):
        small = m.chi_square_test([[55, 45], [65, 35]])
        big = m.chi_square_test([[550, 450], [650, 350]])
        self.assertAlmostEqual(big["chi2"], 10 * small["chi2"], places=9,
                               msg="ten times the people with the same rates gives ten times the chi-square")
        self.assertAlmostEqual(big["cramers_v"], small["cramers_v"], places=12,
                               msg="Cramer's V is an effect size: it does not grow with n")


class TestOnData(unittest.TestCase):
    def check(self, path):
        flows, obs = table_of(path)
        got_flows, got_obs = m.read_table(path)
        self.assertEqual(list(got_flows), flows, "flows sorted by name")
        self.assertEqual([list(r) for r in got_obs], obs,
                         "[completed, not completed] per flow; skip rows with a blank completed")
        exp, chi2, df, v = ref_test(obs)
        s = m.summarise(path)
        self.assertEqual(s["n"], sum(map(sum, obs)))
        self.assertAlmostEqual(s["chi2"], round(chi2, 4), places=4)
        self.assertEqual(s["df"], df)
        self.assertAlmostEqual(s["p_value"], round(m.chi2_sf(chi2, df), 4), places=4)
        self.assertAlmostEqual(s["p_value"], round(math.exp(-chi2 / 2), 4), places=4,
                               msg="with 2 degrees of freedom the p-value is exp(-chi2 / 2)")
        self.assertAlmostEqual(s["cramers_v"], round(v, 4), places=4)
        for i, (c, nc) in enumerate(obs):
            self.assertAlmostEqual(s["rates"][i], round(c / (c + nc), 4), places=4)
            for j in range(2):
                self.assertAlmostEqual(s["expected"][i][j], round(exp[i][j], 2), places=2)
        self.assertEqual(s["small_cells"], [])
        return obs

    def test_committed_data(self):
        self.check(DATA)

    def test_second_dataset(self):
        sys.path.insert(0, HERE)
        import make_data
        sys.path.pop(0)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "signups.csv")
            make_data.write_csv(path, make_data.build(seed=OTHER_SEED)["signups"])
            obs = self.check(path)
            self.assertNotEqual(obs, table_of(DATA)[1], "the second dataset should differ")


if __name__ == "__main__":
    unittest.main()
