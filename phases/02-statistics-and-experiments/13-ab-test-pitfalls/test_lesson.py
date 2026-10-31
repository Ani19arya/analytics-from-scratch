"""Tests for lesson 13. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Expected answers are computed here by a different route, never read from the
solution file:
- two-proportion p-values from the 2 x 2 chi-square statistic and math.erfc;
- chi-square tail probabilities by numerically integrating the chi-square
  density (Simpson's rule), not by the closed form the lesson teaches;
- Holm and Benjamini-Hochberg as reject / keep procedures run at many alphas;
- the peeking false positive rate from a separate seeded simulation.
Everything runs on the committed data AND on a second dataset built in memory
from make_data.build(seed=OTHER_SEED)."""
import ast
import csv
import importlib.util
import math
import os
import random
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DAILY = os.path.join(HERE, "data", "daily.csv")
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")
BANNED = {"statistics", "numpy", "pandas", "scipy", "statsmodels"}
OTHER_SEED = 7
METRICS = ("signups", "saves", "shares")


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


def ref_p(c_a, n_a, c_b, n_b):
    """2 x 2 chi-square without continuity correction; with 1 df, P = erfc(sqrt(chi2 / 2))."""
    cells = [[c_a, n_a - c_a], [c_b, n_b - c_b]]
    total = n_a + n_b
    cols = [c_a + c_b, total - c_a - c_b]
    if 0 in cols:
        return 1.0
    chi2 = 0.0
    for r, n in zip(cells, (n_a, n_b)):
        for k in range(2):
            e = n * cols[k] / total
            chi2 += (r[k] - e) ** 2 / e
    return math.erfc(math.sqrt(chi2 / 2))


def ref_chi2_sf(x, df, steps=20000):
    """Integrate the chi-square density from x to far into the tail."""
    if x <= 0:
        return 1.0
    log_c = -(df / 2) * math.log(2) - math.lgamma(df / 2)

    def pdf(t):
        return math.exp(log_c + (df / 2 - 1) * math.log(t) - t / 2)

    upper = x + 60 + 4 * df
    h = (upper - x) / steps
    total = pdf(x) + pdf(upper)
    for i in range(1, steps):
        total += (4 if i % 2 else 2) * pdf(x + i * h)
    return total * h / 3


def ref_holm_reject(pvalues, alpha):
    order = sorted(range(len(pvalues)), key=lambda i: pvalues[i])
    rejected = set()
    for rank, i in enumerate(order):
        if pvalues[i] <= alpha / (len(pvalues) - rank):
            rejected.add(i)
        else:
            break
    return rejected


def ref_bh_reject(pvalues, alpha):
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    cutoff = -1
    for rank, i in enumerate(order):
        if pvalues[i] <= alpha * (rank + 1) / m:
            cutoff = rank
    return set(order[:cutoff + 1])


def ref_daily(path):
    with open(path, newline="") as f:
        return [dict((k, v if k == "variant" else int(v)) for k, v in r.items()) for r in csv.DictReader(f)]


def ref_totals(rows, last_day=99):
    t = {}
    for r in rows:
        if r["day"] <= last_day:
            cell = t.setdefault(r["variant"], {"users": 0, "signups": 0, "saves": 0, "shares": 0})
            for k in cell:
                cell[k] += r[k]
    return t


def ref_peeking(n_sims, n_days, per_day, rate, seed):
    rng = random.Random(seed)
    any_day = final = 0
    for _ in range(n_sims):
        a = b = 0
        hit = False
        for d in range(1, n_days + 1):
            for _ in range(per_day):
                a += rng.random() < rate
                b += rng.random() < rate
            p = ref_p(a, d * per_day, b, d * per_day)
            hit = hit or p < 0.05
        any_day += hit
        final += p < 0.05
    return any_day / n_sims, final / n_sims


m = load()


class TestRules(unittest.TestCase):
    def test_no_statistics_library(self):
        used = imported_modules(TARGET) & BANNED
        self.assertFalse(used, "Write the tests yourself: remove the import of %s." % ", ".join(sorted(used)))


class TestPieces(unittest.TestCase):
    def test_two_proportion_p(self):
        for case in ((200, 2000, 260, 2000), (107, 976, 135, 924), (5, 40, 5, 40), (0, 10, 3, 12)):
            self.assertAlmostEqual(m.two_proportion_p(*case), ref_p(*case), places=9,
                                   msg="pooled two-proportion z-test, two-sided, for %s" % (case,))
        self.assertEqual(m.two_proportion_p(0, 50, 0, 60), 1.0, "no conversions anywhere: no evidence, p = 1")
        self.assertEqual(m.two_proportion_p(50, 50, 60, 60), 1.0, "everyone converts: p = 1")
        with self.assertRaises(ValueError):
            m.two_proportion_p(0, 0, 1, 10)

    def test_chi2_sf(self):
        self.assertAlmostEqual(m.chi2_sf(3.841458820694124, 1), 0.05, places=9)
        self.assertAlmostEqual(m.chi2_sf(9.487729036781154, 4), 0.05, places=9)
        for df in (1, 2, 3, 4, 5, 6, 9):
            for x in (0.3, 1.0, 2.5, 7.0, 15.0, 30.0):
                self.assertAlmostEqual(m.chi2_sf(x, df), ref_chi2_sf(x, df), places=6,
                                       msg="chi-square tail for x=%s, df=%s" % (x, df))
        self.assertEqual(m.chi2_sf(0, 3), 1.0)
        with self.assertRaises(ValueError):
            m.chi2_sf(2.0, 0)

    def test_srm_check(self):
        counts = {"A": 1000, "B": 1040, "C": 960}
        got = m.srm_check(counts)
        chi2 = sum((n - 1000) ** 2 / 1000 for n in counts.values())
        self.assertAlmostEqual(got["chi2"], chi2, places=9)
        self.assertEqual(got["df"], 2)
        self.assertAlmostEqual(got["p_value"], ref_chi2_sf(chi2, 2), places=6)
        even = m.srm_check({"A": 500, "B": 500})
        self.assertEqual((even["chi2"], even["p_value"]), (0.0, 1.0), "a perfect split: chi2 0, p 1")
        planned = m.srm_check({"A": 900, "B": 100}, {"A": 0.9, "B": 0.1})
        self.assertAlmostEqual(planned["chi2"], 0.0, places=9, msg="use the planned shares, not 50/50")
        with self.assertRaises(ValueError):
            m.srm_check({"A": 10})

    def test_srm_culprits(self):
        counts = {"A": 4000, "B": 4010, "C": 3990, "D": 3600}
        total = sum(counts.values())
        want = []
        for g in sorted(counts):
            z = (counts[g] - total / 4) / math.sqrt(total * 0.25 * 0.75)
            if math.erfc(abs(z) / math.sqrt(2)) < 0.001:
                want.append(g)
        self.assertEqual(list(m.srm_culprits(counts)), want, "test each group against all the others together")
        self.assertEqual(list(m.srm_culprits({"A": 100, "B": 101})), [])

    def test_adjustments_hand_case(self):
        p = [0.01, 0.04, 0.03, 0.005, 0.2]
        self.assertEqual([round(x, 6) for x in m.bonferroni(p)], [0.05, 0.2, 0.15, 0.025, 1.0])
        self.assertEqual([round(x, 6) for x in m.holm(p)], [0.04, 0.09, 0.09, 0.025, 0.2],
                         "Holm: multiply the k-th smallest by (m - k + 1), and never let it fall below the one before")
        self.assertEqual([round(x, 6) for x in m.benjamini_hochberg(p)], [0.025, 0.05, 0.05, 0.025, 0.2],
                         "BH: p * m / rank, then take the running minimum from the largest p down")
        self.assertEqual(list(m.holm([])), [])
        self.assertEqual(list(m.benjamini_hochberg([0.3])), [0.3])
        self.assertEqual([round(x, 6) for x in m.holm([0.02, 0.02])], [0.04, 0.04], "ties get the same adjusted value")

    def test_adjustments_match_procedures(self):
        rng = random.Random(13)
        for _ in range(40):
            size = rng.randrange(2, 15)
            p = [rng.random() ** 3 for _ in range(size)]
            h, q = m.holm(p), m.benjamini_hochberg(p)
            for alpha in (0.01, 0.05, 0.1, 0.25):
                self.assertEqual({i for i in range(size) if h[i] <= alpha}, ref_holm_reject(p, alpha),
                                 "Holm adjusted p <= alpha must reject exactly what the step-down procedure rejects")
                self.assertEqual({i for i in range(size) if q[i] <= alpha}, ref_bh_reject(p, alpha),
                                 "BH adjusted p <= alpha must reject exactly what the step-up procedure rejects")


class TestPeeking(unittest.TestCase):
    def test_simulation(self):
        got = m.simulate_peeking(1500, 14, 60, 0.1, seed=3)
        want = ref_peeking(1500, 14, 60, 0.1, seed=99)
        self.assertEqual(got, m.simulate_peeking(1500, 14, 60, 0.1, seed=3), "the same seed must give the same answer")
        self.assertAlmostEqual(got[1], want[1], delta=0.03, msg="checking only on the last day should be wrong about 5% of the time")
        self.assertAlmostEqual(got[0], want[0], delta=0.05, msg="share of A/A tests below 0.05 on ANY of the 14 days")
        self.assertGreater(got[0], 2 * got[1], "peeking every day should raise false wins well above the final-day rate")
        one = m.simulate_peeking(300, 1, 50, 0.2, seed=1)
        self.assertEqual(one[0], one[1], "with one look, any day and the last day are the same")
        with self.assertRaises(ValueError):
            m.simulate_peeking(0, 5, 10, 0.1)


class TestOnData(unittest.TestCase):
    def check(self, path):
        rows = ref_daily(path)
        got_rows = m.read_daily(path)
        self.assertEqual([dict(r) for r in got_rows], rows, "one dict per row, counts as ints")
        t = ref_totals(rows)
        curve = m.peeking_curve(got_rows, "A", "C", "saves")
        days = sorted({r["day"] for r in rows})
        self.assertEqual([d for d, _ in curve], days)
        for d, p in curve:
            c = ref_totals(rows, d)
            self.assertAlmostEqual(p, ref_p(c["A"]["saves"], c["A"]["users"], c["C"]["saves"], c["C"]["users"]),
                                   places=9, msg="peeking curve: use every user up to and including day %d" % d)
        r = m.analyse(path)
        counts = {g: t[g]["users"] for g in t}
        self.assertEqual(dict(r["users"]), counts)
        chi2 = sum((n - sum(counts.values()) / 5) ** 2 / (sum(counts.values()) / 5) for n in counts.values())
        self.assertAlmostEqual(r["srm_p"], ref_chi2_sf(chi2, 4), delta=1e-6 + 1e-6 * ref_chi2_sf(chi2, 4))
        total = sum(counts.values())
        culprits = [g for g in sorted(counts)
                    if math.erfc(abs(counts[g] - total / 5) / math.sqrt(total * 0.2 * 0.8) / math.sqrt(2)) < 0.001]
        dropped = culprits if ref_chi2_sf(chi2, 4) < 0.001 else []
        self.assertEqual(list(r["dropped"]), dropped, "drop the groups that fail the sample ratio check, and only those")
        expect = []
        for v in sorted(t):
            if v == "A" or v in dropped:
                continue
            for metric in METRICS:
                a, b = t["A"], t[v]
                expect.append((v, metric, round(b[metric] / b["users"] - a[metric] / a["users"], 5),
                               ref_p(a[metric], a["users"], b[metric], b["users"])))
        self.assertEqual([(x["variant"], x["metric"]) for x in r["tests"]], [e[:2] for e in expect],
                         "one test per kept challenger and metric, sorted by variant then signups, saves, shares")
        raw = [e[3] for e in expect]
        for x, e in zip(r["tests"], expect):
            self.assertAlmostEqual(x["lift"], e[2], places=5)
            self.assertAlmostEqual(x["p"], e[3], places=9)
        holm_set = ref_holm_reject(raw, 0.05)
        bh_set = ref_bh_reject(raw, 0.05)
        names = [e[0] + ":" + e[1] for e in expect]
        self.assertEqual(list(r["wins_raw"]), [names[i] for i, e in enumerate(expect) if e[2] > 0 and e[3] < 0.05])
        self.assertEqual(list(r["wins_holm"]), [names[i] for i, e in enumerate(expect) if e[2] > 0 and i in holm_set],
                         "Holm over the whole family of tests you read")
        self.assertEqual(list(r["wins_bh"]), [names[i] for i, e in enumerate(expect) if e[2] > 0 and i in bh_set],
                         "Benjamini-Hochberg over the whole family of tests you read")
        return r

    def test_committed_data(self):
        r = self.check(DAILY)
        self.assertIn("E", r["dropped"], "variant E fails the sample ratio check on the lesson data")

    def test_second_dataset(self):
        sys.path.insert(0, HERE)
        import make_data
        sys.path.pop(0)
        with tempfile.TemporaryDirectory() as folder:
            make_data.write_all(folder, make_data.build(seed=OTHER_SEED))
            r = self.check(os.path.join(folder, "daily.csv"))
            self.assertNotEqual(dict(r["users"]), {g: n for g, n in m.analyse(DAILY)["users"].items()},
                                "the second dataset should differ")


if __name__ == "__main__":
    unittest.main()
