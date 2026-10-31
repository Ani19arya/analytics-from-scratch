"""Tests for lesson 08: retention curves and churn. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Every expected number is computed here in plain Python, never read from the solution.
The tests run on the committed data and on a second dataset built with another seed."""
import csv
import datetime
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
AS_OF = datetime.date(2026, 10, 31)
OTHER_SEED = 8
DAYS = (1, 7, 14, 30)
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")


def load():
    spec = importlib.util.spec_from_file_location("lesson_module", TARGET)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load()
sys.path.insert(0, HERE)
import make_data  # noqa: E402


def d(text):
    return datetime.datetime.strptime(text, "%Y-%m-%d").date()


def reference(folder, n, as_of=AS_OF):
    """Independent route: for each user, the list of visit dates, then compare
    dates directly (signup + n days) instead of building offsets."""
    with open(os.path.join(folder, "users.csv"), newline="") as f:
        users = {r["user_id"]: d(r["signup_date"]) for r in csv.DictReader(f)}
    visits = {}
    with open(os.path.join(folder, "visits.csv"), newline="") as f:
        for r in csv.DictReader(f):
            visits.setdefault(r["user_id"], []).append(d(r["visit_date"]))
    target = {u: s + datetime.timedelta(days=n) for u, s in users.items()}
    elig = [u for u in users if target[u] <= as_of]
    classic = sum(1 for u in elig if target[u] in visits.get(u, []))
    unbounded = sum(1 for u in elig if any(v >= target[u] for v in visits.get(u, [])))
    return classic, unbounded, len(elig), users, visits


def write_tables(folder, users, visits):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "users.csv"), "w", newline="") as f:
        f.write("user_id,signup_date\n" + "".join("%s,%s\n" % u for u in users))
    with open(os.path.join(folder, "visits.csv"), "w", newline="") as f:
        f.write("user_id,visit_date\n" + "".join("%s,%s\n" % v for v in visits))


class TestSmallCases(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def small(self, users, visits):
        write_tables(self.tmp, users, visits)
        return m.load(os.path.join(self.tmp, "users.csv"), os.path.join(self.tmp, "visits.csv"))

    def test_load_drops_pre_signup_and_keeps_silent_users(self):
        s, o = self.small([("a", "2026-10-01"), ("b", "2026-10-01")],
                          [("a", "2026-09-29"), ("a", "2026-10-01"), ("a", "2026-10-08"), ("zz", "2026-10-02")])
        self.assertEqual(o["a"], {0, 7}, "a visit dated before signup is a glitch and must be dropped")
        self.assertIn("b", o, "a user with no visits still belongs to the cohort (an empty set)")
        self.assertEqual(o["b"], set())
        self.assertNotIn("zz", o, "visits by a user who is not in users.csv are dropped")

    def test_classic_vs_unbounded(self):
        s, o = self.small([("a", "2026-10-01"), ("b", "2026-10-01"), ("c", "2026-10-01")],
                          [("a", "2026-10-08"), ("b", "2026-10-12"), ("c", "2026-10-01")])
        self.assertEqual(m.classic_retention(s, o, 7, AS_OF), (1, 3), "only a visited on exactly day 7")
        self.assertEqual(m.unbounded_retention(s, o, 7, AS_OF), (2, 3),
                         "a (day 7) and b (day 11) both visited on day 7 or later")

    def test_censoring_boundary(self):
        s, o = self.small([("old", "2026-10-01"), ("young", "2026-10-02")], [])
        self.assertEqual(m.classic_retention(s, o, 30, AS_OF)[1], 1,
                         "signed up 1 Oct, day 30 is 31 Oct = as_of, so eligible; 2 Oct is too young")
        self.assertEqual(m.rate((0, 0)), None, "no eligible users: the rate is unknown (None), not 0")
        self.assertEqual(m.rate((1, 4)), 0.25)

    def test_empty(self):
        s, o = self.small([], [])
        self.assertEqual(m.classic_retention(s, o, 7, AS_OF), (0, 0))
        self.assertEqual(m.cohort_curves(s, o, DAYS, AS_OF), {})

    def test_cohort_too_young_is_none(self):
        s, o = self.small([("a", "2026-10-26"), ("b", "2026-10-27")], [("a", "2026-10-27")])
        curves = m.cohort_curves(s, o, (1, 7), AS_OF)
        self.assertEqual(list(curves), ["2026-10-26"], "cohorts are keyed by the Monday of the signup week")
        self.assertEqual(curves["2026-10-26"][1], 0.5)
        self.assertIsNone(curves["2026-10-26"][7], "nobody in this cohort has reached day 7: None, not 0.0")


class OnDataMixin:
    folder = DATA

    def loaded(self):
        return m.load(os.path.join(self.folder, "users.csv"), os.path.join(self.folder, "visits.csv"))

    def test_overall_retention(self):
        s, o = self.loaded()
        for n in DAYS:
            classic, unbounded, elig, _, _ = reference(self.folder, n)
            self.assertEqual(m.classic_retention(s, o, n, AS_OF), (classic, elig),
                             "day %d classic: expected (%d, %d)" % (n, classic, elig))
            self.assertEqual(m.unbounded_retention(s, o, n, AS_OF), (unbounded, elig),
                             "day %d unbounded: expected (%d, %d)" % (n, unbounded, elig))

    def test_unbounded_never_below_classic(self):
        s, o = self.loaded()
        for n in DAYS:
            self.assertGreaterEqual(m.unbounded_retention(s, o, n, AS_OF)[0], m.classic_retention(s, o, n, AS_OF)[0])

    def test_cohort_curves(self):
        s, o = self.loaded()
        _, _, _, users, visits = reference(self.folder, 0)
        curves = m.cohort_curves(s, o, DAYS, AS_OF, kind="unbounded")
        for wk, row in curves.items():
            monday = d(wk)
            members = [u for u, sd in users.items() if 0 <= (sd - monday).days < 7]
            self.assertTrue(members, "cohort %s has no users" % wk)
            for n in DAYS:
                elig = [u for u in members if (AS_OF - users[u]).days >= n]
                if not elig:
                    self.assertIsNone(row[n], "%s day %d: no user is old enough, expected None" % (wk, n))
                    continue
                hit = sum(1 for u in elig if any((v - users[u]).days >= n for v in visits.get(u, [])))
                self.assertAlmostEqual(row[n], hit / len(elig), places=9,
                                       msg="%s day %d: expected %d / %d" % (wk, n, hit, len(elig)))
        self.assertEqual(sum(1 for u in users if m.week_start(users[u]) in curves), len(users))


class TestOnData(OnDataMixin, unittest.TestCase):
    pass


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.folder = cls.tmp
        make_data.write_all(make_data.build(seed=OTHER_SEED), cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
