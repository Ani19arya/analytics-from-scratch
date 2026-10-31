"""Tests for lesson 07. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Expected answers come from Python's statistics module and plain formulas here,
never from the solution file. The summary is checked on the committed data AND
on a second dataset built in memory with another seed.

How the simulation is checked. Your sample_means may use the random numbers in a
different order from the solution, so its means will not match exactly. Their
mean and SD must match theory within 5 standard errors, computed here from the
population itself:
- the mean of D sample means has SE  sigma / sqrt(n) / sqrt(D);
- their SD has SE about sqrt(m4 - v^2) / (2 * sd * sqrt(D)), where v = sigma^2 / n
  is the variance of one mean and m4 = (mu4 + 3 * (n - 1) * sigma^4) / n^3 its
  fourth central moment (mu4 is the population's fourth central moment).
A correct simulation lands outside 5 standard errors less than once in a million
times, and with a fixed seed it gives the same result on every run. Sampling
without replacement (rng.sample) shrinks the SD by under 1% here and also passes."""
import ast
import csv
import importlib.util
import math
import os
import statistics
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
POP = os.path.join(HERE, "data", "population.csv")
WEEKS = os.path.join(HERE, "data", "weeks.csv")
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")
BANNED = {"statistics", "numpy", "pandas", "scipy", "statsmodels"}
OTHER_SEED = 41
DRAWS = 10000


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


def column(path):
    with open(path, newline="") as f:
        return [float(r["order_value"]) for r in csv.DictReader(f)]


def weeks_of(path):
    out = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            out.setdefault(r["week_start"], []).append(float(r["order_value"]))
    return out


def theory(pop, n, draws):
    """Expected centre and spread of the sample means, and the 5-SE tolerances."""
    mu, sigma = statistics.mean(pop), statistics.pstdev(pop)
    mu4 = sum((x - mu) ** 4 for x in pop) / len(pop)
    v = sigma ** 2 / n
    m4 = (mu4 + 3 * (n - 1) * sigma ** 4) / n ** 3
    sd = math.sqrt(v)
    return {"mu": mu, "sd": sd, "tol_mean": 5 * sd / math.sqrt(draws),
            "tol_sd": 5 * math.sqrt(m4 - v ** 2) / (2 * sd * math.sqrt(draws))}


m = load()


class TestRules(unittest.TestCase):
    def test_no_statistics_module(self):
        used = imported_modules(TARGET) & BANNED
        self.assertFalse(used, "Write the formulas yourself: remove the import of %s." % ", ".join(sorted(used)))


class TestFormulas(unittest.TestCase):
    vals = [2, 4, 4, 4, 5, 5, 7, 9]

    def test_mean(self):
        self.assertAlmostEqual(m.mean(self.vals), 5.0)
        self.assertAlmostEqual(m.mean([0, 0, 0, 10]), 2.5, msg="zeros count in the mean")
        with self.assertRaises(ValueError):
            m.mean([])

    def test_population_sd(self):
        self.assertAlmostEqual(m.population_sd(self.vals), statistics.pstdev(self.vals), places=9,
                               msg="for a whole population divide by N: here sqrt(32 / 8) = 2.0")
        self.assertEqual(m.population_sd([7]), 0, "one value has no spread")

    def test_sample_sd_uses_n_minus_1(self):
        self.assertAlmostEqual(m.sample_sd(self.vals), statistics.stdev(self.vals), places=9,
                               msg="for a sample divide by n - 1: here sqrt(32 / 7) = 2.138, not 2.0")
        self.assertEqual(m.sample_sd([5, 5]), 0, "a tie has no spread")
        for vals in ([5], []):
            with self.assertRaises(ValueError, msg="a sample SD needs at least 2 values"):
                m.sample_sd(vals)

    def test_standard_error(self):
        self.assertAlmostEqual(m.standard_error(self.vals), statistics.stdev(self.vals) / math.sqrt(8), places=9,
                               msg="SE is the sample SD divided by sqrt(n)")
        self.assertAlmostEqual(m.standard_error([1, 3]), math.sqrt(2) / math.sqrt(2))

    def test_share_within(self):
        vals = [1, 2, 3, 4, 5]
        self.assertAlmostEqual(m.share_within(vals, 3, 1), 3 / 5, msg="both ends count: 2, 3 and 4")
        self.assertAlmostEqual(m.share_within(vals, 3, 0), 1 / 5)
        self.assertAlmostEqual(m.share_within(vals, 30, 1), 0.0)
        with self.assertRaises(ValueError):
            m.share_within([], 0, 1)


class TestSampling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pop = column(POP)
        cls.means = m.sample_means(cls.pop, 18, DRAWS, 3)

    def test_shape_and_seed(self):
        self.assertEqual(len(self.means), DRAWS, "one mean per draw")
        self.assertEqual(m.sample_means(self.pop, 18, 20, 9), m.sample_means(self.pop, 18, 20, 9),
                         "make one random.Random(seed) inside the function, so a seed repeats exactly")
        self.assertNotEqual(m.sample_means(self.pop, 18, 20, 9), m.sample_means(self.pop, 18, 20, 10))
        self.assertGreater(len(set(self.means)), DRAWS // 2,
                           "the samples look alike: create the generator once, not once per draw")

    def test_centre_and_spread_match_theory(self):
        t = theory(self.pop, 18, DRAWS)
        centre = statistics.mean(self.means)
        spread = statistics.stdev(self.means)
        self.assertLess(abs(centre - t["mu"]), t["tol_mean"],
                        "the means should centre on the population mean %.2f, got %.2f" % (t["mu"], centre))
        self.assertLess(abs(spread - t["sd"]), t["tol_sd"],
                        "the means should spread by sigma / sqrt(18) = %.3f, got %.3f; is each sample 18 values?"
                        % (t["sd"], spread))

    def test_bigger_samples_wobble_less(self):
        t = theory(self.pop, 72, DRAWS)
        spread = statistics.stdev(m.sample_means(self.pop, 72, DRAWS, 4))
        self.assertLess(abs(spread - t["sd"]), t["tol_sd"],
                        "four times the sample size should halve the wobble, to %.3f" % t["sd"])

    def test_edges(self):
        self.assertEqual(m.sample_means([5.0], 3, 4, 1), [5.0] * 4, "a population of one value always gives that value")
        self.assertEqual(m.sample_means(self.pop, 18, 0, 1), [])
        with self.assertRaises(ValueError):
            m.sample_means([], 3, 4, 1)
        with self.assertRaises(ValueError):
            m.sample_means(self.pop, 0, 4, 1)


class TestSummary(unittest.TestCase):
    def check(self, pop_path, weeks_path):
        pop = column(pop_path)
        weeks = weeks_of(weeks_path)
        first, second = sorted(weeks)
        s = m.summarise(pop_path, weeks_path, n=18, draws=DRAWS, seed=2)
        mu, sigma = statistics.mean(pop), statistics.pstdev(pop)
        self.assertAlmostEqual(s["pop_mean"], mu, places=6)
        self.assertAlmostEqual(s["pop_sd"], sigma, places=6, msg="the population is complete, so divide by N")
        self.assertAlmostEqual(s["true_se"], sigma / math.sqrt(18), places=6)
        t = theory(pop, 18, DRAWS)
        self.assertLess(abs(s["mean_of_means"] - t["mu"]), t["tol_mean"])
        self.assertLess(abs(s["sd_of_means"] - t["sd"]), t["tol_sd"],
                        "sd_of_means should be near sigma / sqrt(18) = %.3f" % t["sd"])
        means = m.sample_means(pop, 18, DRAWS, 2)
        within = sum(1 for x in means if abs(x - mu) <= 1.96 * sigma / math.sqrt(18)) / DRAWS
        self.assertAlmostEqual(s["share_within_1_96"], within, places=9,
                               msg="share_within_1_96 should use the same means as sample_means(pop, 18, draws, seed)")
        se1 = statistics.stdev(weeks[first]) / math.sqrt(len(weeks[first]))
        se2 = statistics.stdev(weeks[second]) / math.sqrt(len(weeks[second]))
        self.assertAlmostEqual(s["week1_mean"], statistics.mean(weeks[first]), places=6, msg="week 1 is the earliest week_start")
        self.assertAlmostEqual(s["week2_mean"], statistics.mean(weeks[second]), places=6)
        self.assertAlmostEqual(s["week1_se"], se1, places=6, msg="a real week is a sample: use the n - 1 SD")
        self.assertAlmostEqual(s["week2_se"], se2, places=6)
        self.assertAlmostEqual(s["change"], statistics.mean(weeks[second]) - statistics.mean(weeks[first]), places=6)
        self.assertAlmostEqual(s["change_se"], math.sqrt(se1 ** 2 + se2 ** 2), places=6,
                               msg="the wobble of a difference adds the squared SEs, then takes the root")

    def test_readers(self):
        self.assertEqual(m.read_orders(POP), column(POP))
        self.assertEqual(m.read_weeks(WEEKS), weeks_of(WEEKS))

    def test_committed_data(self):
        self.check(POP, WEEKS)

    def test_second_dataset(self):
        sys.path.insert(0, HERE)
        import make_data
        sys.path.pop(0)
        with tempfile.TemporaryDirectory() as folder:
            make_data.write_all(folder, make_data.build(seed=OTHER_SEED))
            pop_path = os.path.join(folder, "population.csv")
            self.assertNotEqual(column(pop_path), column(POP), "the second dataset should differ")
            self.check(pop_path, os.path.join(folder, "weeks.csv"))


if __name__ == "__main__":
    unittest.main()
