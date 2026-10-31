"""Tests for lesson 12. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Expected answers are computed here, never read from the solution file:
- the median and percentiles come from the statistics module (median, and
  quantiles with method="inclusive", which interpolates at q * (n - 1));
- the bootstraps are rebuilt below with the resampling rule the exercise
  states, so a correct answer matches to the cent.
Everything runs on the committed data AND on a second dataset built in memory
from make_data.build(seed=OTHER_SEED)."""
import ast
import csv
import importlib.util
import os
import random
import statistics
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ORDERS = os.path.join(HERE, "data", "orders.csv")
SESSIONS = os.path.join(HERE, "data", "sessions.csv")
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")
BANNED = {"statistics", "numpy", "pandas", "scipy", "statsmodels"}
OTHER_SEED = 5
N_BOOT = 1000


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


def orders_of(path):
    with open(path, newline="") as f:
        return [float(r["order_value"]) for r in csv.DictReader(f) if r["order_value"] != ""]


def sessions_of(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append((int(r["user_id"]), float(r["revenue"])))
    per_session = [(1, rev) for _, rev in rows]
    ids = sorted({u for u, _ in rows})
    per_user = [(sum(1 for u, _ in rows if u == i), sum(rev for u, rev in rows if u == i)) for i in ids]
    return per_session, per_user


def ref_ratio(pairs):
    return sum(p[1] for p in pairs) / sum(p[0] for p in pairs)


def ref_boot(units, stat, n_boot, seed):
    rng = random.Random(seed)
    return [stat(rng.choices(units, k=len(units))) for _ in range(n_boot)]


def ref_interval(stats):
    cuts = statistics.quantiles(stats, n=40, method="inclusive")
    return cuts[0], cuts[-1]


m = load()


class TestRules(unittest.TestCase):
    def test_no_statistics_library(self):
        used = imported_modules(TARGET) & BANNED
        self.assertFalse(used, "Write the bootstrap yourself: remove the import of %s." % ", ".join(sorted(used)))


class TestPieces(unittest.TestCase):
    def test_median(self):
        self.assertEqual(m.median([5.0, 1.0, 3.0]), 3.0)
        self.assertEqual(m.median([4.0, 1.0, 3.0, 2.0]), 2.5, "even count: average the two middle values")
        self.assertEqual(m.median([7.0]), 7.0)
        with self.assertRaises(ValueError):
            m.median([])

    def test_ratio_of_sums(self):
        self.assertAlmostEqual(m.ratio_of_sums([(1, 10.0), (3, 0.0), (1, 30.0)]), 8.0,
                               msg="total revenue 40 over total sessions 5, not the average of per-user ratios")
        with self.assertRaises(ValueError):
            m.ratio_of_sums([(0, 5.0), (0, 1.0)])

    def test_percentile(self):
        data = [10.0, 20.0, 30.0, 40.0, 50.0]
        self.assertEqual(m.percentile(data, 0), 10.0)
        self.assertEqual(m.percentile(data, 1), 50.0)
        self.assertAlmostEqual(m.percentile(data, 0.5), 30.0)
        self.assertAlmostEqual(m.percentile([50.0, 10.0, 40.0, 20.0, 30.0], 0.1), 14.0,
                               msg="sort first, then position q * (n - 1) = 0.4, 40% of the way from 10 to 20")
        self.assertEqual(m.percentile([3.0], 0.975), 3.0)
        for bad in ((data, 1.5), (data, -0.1), ([], 0.5)):
            with self.assertRaises(ValueError):
                m.percentile(*bad)

    def test_percentile_interval_matches_quantiles(self):
        rng = random.Random(3)
        stats = [rng.gauss(0, 1) for _ in range(321)]
        low, high = m.percentile_interval(stats)
        want = ref_interval(stats)
        self.assertAlmostEqual(low, want[0], places=12, msg="2.5th percentile with linear interpolation")
        self.assertAlmostEqual(high, want[1], places=12)
        cuts = statistics.quantiles(stats, n=20, method="inclusive")
        low, high = m.percentile_interval(stats, level=0.9)
        self.assertAlmostEqual(low, cuts[0], places=12)
        self.assertAlmostEqual(high, cuts[-1], places=12)


class TestBootstrap(unittest.TestCase):
    def test_follows_the_rule(self):
        units = [3.0, 9.0, 1.0, 4.0, 7.0, 2.0]
        got = m.bootstrap(units, m.median, n_boot=50, seed=11)
        self.assertEqual(len(got), 50)
        self.assertEqual(list(got), ref_boot(units, lambda s: m.median(s), 50, 11),
                         "one random.Random(seed), and rng.choices(units, k=len(units)) for each resample")

    def test_seed_repeats_and_inputs_kept(self):
        units = [(2, 10.0), (1, 0.0), (4, 50.0)]
        before = list(units)
        a = m.bootstrap(units, m.ratio_of_sums, 30, 4)
        b = m.bootstrap(units, m.ratio_of_sums, 30, 4)
        self.assertEqual(a, b, "the same seed must give the same resamples")
        self.assertEqual(units, before, "do not change the caller's list")

    def test_one_unit(self):
        self.assertEqual(set(m.bootstrap([42.0], m.median, 20, 1)), {42.0},
                         "one unit: every resample is that unit")

    def test_errors(self):
        with self.assertRaises(ValueError):
            m.bootstrap([], m.median, 10, 1)
        with self.assertRaises(ValueError):
            m.bootstrap([1.0, 2.0], m.median, 0, 1)


class TestOnData(unittest.TestCase):
    def check(self, orders_path, sessions_path):
        orders = orders_of(orders_path)
        per_session, per_user = sessions_of(sessions_path)
        self.assertEqual(list(m.read_orders(orders_path)), orders, "order values in file order, blanks skipped")
        got_s, got_u = m.read_sessions(sessions_path)
        self.assertEqual([tuple(p) for p in got_s], per_session, "one (1, revenue) pair per session, in file order")
        self.assertEqual([p[0] for p in got_u], [p[0] for p in per_user],
                         "one (sessions, total revenue) pair per user, sorted by user_id")
        for got, want in zip(got_u, per_user):
            self.assertAlmostEqual(got[1], want[1], places=6, msg="total revenue per user")
        s = m.summarise(orders_path, sessions_path, n_boot=N_BOOT, seed=2)
        self.assertEqual(s["n_orders"], len(orders))
        self.assertAlmostEqual(s["median"], round(statistics.median(orders), 2), delta=0.011)
        want = ref_interval(ref_boot(orders, statistics.median, N_BOOT, 2))
        self.assertAlmostEqual(s["median_ci"][0], round(want[0], 2), delta=0.011, msg="median interval, low end")
        self.assertAlmostEqual(s["median_ci"][1], round(want[1], 2), delta=0.011, msg="median interval, high end")
        self.assertEqual((s["n_users"], s["n_sessions"]), (len(per_user), len(per_session)))
        self.assertAlmostEqual(s["revenue_per_session"], round(ref_ratio(per_user), 2), delta=0.011)
        users = ref_interval(ref_boot(per_user, ref_ratio, N_BOOT, 2))
        sessions = ref_interval(ref_boot(per_session, ref_ratio, N_BOOT, 2))
        self.assertAlmostEqual(s["ratio_ci_users"][0], round(users[0], 2), delta=0.011,
                               msg="resample whole users: their (sessions, revenue) pairs")
        self.assertAlmostEqual(s["ratio_ci_users"][1], round(users[1], 2), delta=0.011)
        self.assertAlmostEqual(s["ratio_ci_sessions"][0], round(sessions[0], 2), delta=0.011)
        self.assertAlmostEqual(s["ratio_ci_sessions"][1], round(sessions[1], 2), delta=0.011)
        return s["median"]

    def test_committed_data(self):
        self.check(ORDERS, SESSIONS)

    def test_second_dataset(self):
        sys.path.insert(0, HERE)
        import make_data
        sys.path.pop(0)
        with tempfile.TemporaryDirectory() as folder:
            make_data.write_all(folder, make_data.build(seed=OTHER_SEED))
            med = self.check(os.path.join(folder, "orders.csv"), os.path.join(folder, "sessions.csv"))
            self.assertNotEqual(med, round(statistics.median(orders_of(ORDERS)), 2), "the second dataset should differ")


if __name__ == "__main__":
    unittest.main()
