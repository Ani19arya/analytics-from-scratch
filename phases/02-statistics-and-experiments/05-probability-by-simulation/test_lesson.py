"""Tests for lesson 05. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Expected answers come from exact fractions (fractions.Fraction) and plain loops
here, never from the solution file. The summary is checked on the committed data
AND on a second dataset built in memory with another seed.

How the simulation is checked. Your simulation may use the random numbers in a
different order from the solution, so its counts will not match exactly. They
must still match the exact distribution within simulation noise:
- the mean of the counts must be within 5 standard errors of n * p;
- the simulated tail share must be within 5 standard errors of the exact one;
- the whole simulated distribution (its CDF) must be within 0.03 of the exact
  CDF everywhere. By the Dvoretzky-Kiefer-Wolfowitz inequality a correct
  simulation of 10,000 days misses that by chance with probability below
  2 * exp(-2 * 10000 * 0.03**2), about 3 in 100 million.
A correct simulation fails 5 standard errors less than once in a million times,
and with a fixed seed it gives the same result on every run."""
import ast
import csv
import importlib.util
import math
import os
import sys
import tempfile
import unittest
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "visitors.csv")
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")
BANNED = {"statistics", "numpy", "pandas", "scipy", "statsmodels"}
OTHER_SEED = 31
RUNS = 10000


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


def exact_pmf(k, n, p):
    """Exact binomial probability as a Fraction; p is a Fraction."""
    if k < 0 or k > n:
        return Fraction(0)
    return math.comb(n, k) * p ** k * (1 - p) ** (n - k)


def exact_at_least(k, n, p):
    return sum((exact_pmf(j, n, p) for j in range(max(k, 0), n + 1)), Fraction(0))


def read_counts(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    return len(rows), sum(int(r["bought"]) for r in rows)


m = load()


class TestRules(unittest.TestCase):
    def test_no_statistics_module(self):
        used = imported_modules(TARGET) & BANNED
        self.assertFalse(used, "Write the arithmetic yourself: remove the import of %s." % ", ".join(sorted(used)))


class TestExact(unittest.TestCase):
    def test_pmf_small_by_hand(self):
        # 3 visitors at 50%: 1, 3, 3, 1 ways out of 8
        for k, want in enumerate([1 / 8, 3 / 8, 3 / 8, 1 / 8]):
            self.assertAlmostEqual(m.binom_pmf(k, 3, 0.5), want, places=12,
                                   msg="P(X = %d) for 3 fair coins should be %s" % (k, want))

    def test_pmf_matches_exact_fractions(self):
        p = Fraction(1, 10)
        for k in (0, 1, 20, 30, 45):
            want = float(exact_pmf(k, 200, p))
            self.assertAlmostEqual(m.binom_pmf(k, 200, 0.1) / want, 1, places=9,
                                   msg="binom_pmf(%d, 200, 0.1) should be comb(200, %d) * 0.1^%d * 0.9^%d" % (k, k, k, 200 - k))

    def test_pmf_out_of_range_and_zero_rate(self):
        self.assertEqual(m.binom_pmf(-1, 10, 0.3), 0.0)
        self.assertEqual(m.binom_pmf(11, 10, 0.3), 0.0, "more buyers than visitors is impossible")
        self.assertEqual(m.binom_pmf(0, 10, 0.0), 1.0, "with p = 0 nobody buys, so 0 buyers is certain")
        self.assertEqual(m.binom_pmf(0, 0, 0.4), 1.0, "with no visitors, 0 buyers is certain")
        with self.assertRaises(ValueError, msg="a rate above 1 is not a probability"):
            m.binom_pmf(1, 10, 1.5)

    def test_pmf_sums_to_one(self):
        self.assertAlmostEqual(sum(m.binom_pmf(k, 200, 0.1) for k in range(201)), 1.0, places=12)

    def test_at_least_is_not_exactly(self):
        want = float(exact_at_least(30, 200, Fraction(1, 10)))
        got = m.binom_at_least(30, 200, 0.1)
        self.assertAlmostEqual(got / want, 1, places=9,
                               msg="P(X >= 30) adds P(30) + P(31) + ... + P(200); expected %.6f" % want)
        self.assertGreater(got, m.binom_pmf(30, 200, 0.1) * 2,
                           "30 or more is much more likely than exactly 30")

    def test_at_least_edges(self):
        self.assertEqual(m.binom_at_least(0, 200, 0.1), 1.0)
        self.assertEqual(m.binom_at_least(-3, 200, 0.1), 1.0)
        self.assertEqual(m.binom_at_least(201, 200, 0.1), 0.0)
        self.assertEqual(m.binom_at_least(1, 50, 0.0), 0.0, "with p = 0 nobody ever buys")
        self.assertAlmostEqual(m.binom_at_least(200, 200, 1.0), 1.0)


class TestShares(unittest.TestCase):
    def test_shares_with_ties(self):
        counts = [28, 30, 30, 31, 12]
        self.assertAlmostEqual(m.share_at_least(counts, 30), 3 / 5, msg="30, 30 and 31 are at least 30")
        self.assertAlmostEqual(m.share_exactly(counts, 30), 2 / 5)
        self.assertAlmostEqual(m.share_at_least(counts, 0), 1.0)
        self.assertAlmostEqual(m.share_exactly(counts, 99), 0.0)

    def test_empty_raises(self):
        for fn in (m.share_at_least, m.share_exactly):
            with self.assertRaises(ValueError, msg="%s([]) has no days to count" % fn.__name__):
                fn([], 3)

    def test_simulation_se(self):
        self.assertAlmostEqual(m.simulation_se(0.5, 100), 0.05)
        self.assertEqual(m.simulation_se(0.0, 100), 0.0)
        with self.assertRaises(ValueError):
            m.simulation_se(0.5, 0)


class TestSimulation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.counts = m.simulate_counts(200, 0.1, RUNS, 3)

    def test_shape(self):
        self.assertEqual(len(self.counts), RUNS, "one count per simulated day")
        self.assertTrue(all(isinstance(c, int) and 0 <= c <= 200 for c in self.counts),
                        "every count is a whole number from 0 to 200")

    def test_same_seed_same_answer(self):
        self.assertEqual(m.simulate_counts(200, 0.1, 50, 9), m.simulate_counts(200, 0.1, 50, 9),
                         "make one random.Random(seed) inside the function, so a seed repeats exactly")
        self.assertNotEqual(m.simulate_counts(200, 0.1, 50, 9), m.simulate_counts(200, 0.1, 50, 10),
                            "a different seed should give different days")

    def test_days_are_not_copies(self):
        self.assertGreater(len(set(self.counts)), 10,
                           "the days all look alike: create the generator once, not once per day")

    def test_mean_within_noise(self):
        mean = sum(self.counts) / RUNS
        se = math.sqrt(200 * 0.1 * 0.9 / RUNS)
        self.assertLess(abs(mean - 20), 5 * se,
                        "the average simulated day should have about n * p = 20 buyers, got %.3f" % mean)

    def test_distribution_matches_exact(self):
        p = Fraction(1, 10)
        cdf, worst = Fraction(0), 0.0
        for k in range(201):
            cdf += exact_pmf(k, 200, p)
            emp = sum(1 for c in self.counts if c <= k) / RUNS
            worst = max(worst, abs(emp - float(cdf)))
        self.assertLess(worst, 0.03, "the simulated distribution is %.3f away from the exact one; "
                                     "a visitor should buy when rng.random() < p" % worst)

    def test_edges(self):
        self.assertEqual(m.simulate_counts(10, 0.0, 5, 1), [0] * 5)
        self.assertEqual(m.simulate_counts(10, 1.0, 5, 1), [10] * 5, "with p = 1 every visitor buys")
        self.assertEqual(m.simulate_counts(0, 0.3, 4, 1), [0] * 4)
        self.assertEqual(m.simulate_counts(10, 0.3, 0, 1), [])
        with self.assertRaises(ValueError):
            m.simulate_counts(10, -0.1, 5, 1)


class TestSummary(unittest.TestCase):
    def check(self, path, seed=1):
        n, k = read_counts(path)
        p = Fraction(1, 10)
        s = m.summarise(path, p=0.10, runs=RUNS, seed=seed)
        self.assertEqual((s["visitors"], s["buyers"]), (n, k))
        self.assertAlmostEqual(s["expected"], n * 0.1)
        self.assertAlmostEqual(s["sd"], math.sqrt(n * 0.1 * 0.9), places=9)
        exactly, at_least = float(exact_pmf(k, n, p)), float(exact_at_least(k, n, p))
        self.assertAlmostEqual(s["p_exactly"], exactly, places=12, msg="p_exactly is P(X = %d), the exact formula" % k)
        self.assertAlmostEqual(s["p_at_least"], at_least, places=12,
                               msg="p_at_least is P(X >= %d), the exact sum from %d to %d" % (k, k, n))
        tol = 5 * math.sqrt(at_least * (1 - at_least) / RUNS)
        self.assertLess(abs(s["sim_at_least"] - at_least), tol,
                        "the simulated share of days with %d or more buyers should be near %.4f" % (k, at_least))
        self.assertAlmostEqual(s["sim_se"], math.sqrt(s["sim_at_least"] * (1 - s["sim_at_least"]) / RUNS))

    def test_count_buyers(self):
        self.assertEqual(m.count_buyers(DATA), read_counts(DATA))

    def test_committed_data(self):
        self.check(DATA)

    def test_second_dataset(self):
        sys.path.insert(0, HERE)
        import make_data
        sys.path.pop(0)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "visitors.csv")
            make_data.write_csv(path, make_data.build(seed=OTHER_SEED)["visitors"])
            self.assertNotEqual(read_counts(path), read_counts(DATA), "the second dataset should differ")
            self.check(path, seed=4)


if __name__ == "__main__":
    unittest.main()
