"""Tests for lesson 13: marketplace metrics and liquidity. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Every expected number is computed here independently, with SQLite queries over the CSV
rows (whole seconds for the 48-hour window, text comparison for open posts). The tests
run on the committed data and on a second dataset built with another seed."""
import csv
import datetime
import importlib.util
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OTHER_SEED = 8
AS_OF = "2026-11-01 00:00"
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


def t(text):
    return datetime.datetime.strptime(text, "%Y-%m-%d %H:%M") if text else None


def post(pid, posted, closed="", city="X", category="k"):
    return {"post_id": pid, "city": city, "category": category, "posted_at": t(posted), "closed_at": t(closed)}


def app(pid, applied):
    return {"application_id": "a", "post_id": pid, "worker_id": "w", "applied_at": t(applied)}


def search(when, city="X", category="k"):
    return {"search_id": "s", "worker_id": "w", "city": city, "category": category, "searched_at": t(when)}


def reference(folder):
    """Independent route: SQLite over the raw text rows."""
    con = sqlite3.connect(":memory:")
    for name in ("posts", "applications", "searches"):
        with open(os.path.join(folder, name + ".csv"), newline="") as f:
            rows = list(csv.DictReader(f))
        cols = list(rows[0].keys())
        con.execute("CREATE TABLE %s (%s)" % (name, ", ".join(cols)))
        con.executemany("INSERT INTO %s VALUES (%s)" % (name, ",".join("?" * len(cols))),
                        [[r[c] for c in cols] for r in rows])
    liq = {}
    q = """
    SELECT p.city,
           MAX(CASE WHEN a.post_id IS NOT NULL THEN 1 ELSE 0 END) AS filled
    FROM posts p
    LEFT JOIN applications a
      ON a.post_id = p.post_id
     AND strftime('%s', a.applied_at) - strftime('%s', p.posted_at) BETWEEN 0 AND 172800
    WHERE strftime('%s', ?) - strftime('%s', p.posted_at) >= 172800
    GROUP BY p.post_id, p.city"""
    for city, filled in con.execute(q, [AS_OF]):
        for key in (city, "all"):
            f, e = liq.get(key, (0, 0))
            liq[key] = (f + filled, e + 1)
    suc = {}
    q = """
    SELECT s.city, s.search_id,
           EXISTS (SELECT 1 FROM posts p WHERE p.city = s.city AND p.category = s.category
                   AND p.posted_at <= s.searched_at AND (p.closed_at = '' OR s.searched_at < p.closed_at))
    FROM searches s"""
    for city, _, hit in con.execute(q):
        for key in (city, "all"):
            f, n = suc.get(key, (0, 0))
            suc[key] = (f + hit, n + 1)
    con.close()
    return liq, suc


class TestSmallCases(unittest.TestCase):
    AS_OF = t(AS_OF)

    def test_window_boundary(self):
        posts = [post("p1", "2026-10-01 10:00"), post("p2", "2026-10-01 10:00"), post("p3", "2026-10-01 10:00")]
        apps = [app("p1", "2026-10-03 10:00"), app("p2", "2026-10-03 10:01"), app("p2", "2026-10-09 09:00"),
                app("nope", "2026-10-01 11:00")]
        got = m.post_liquidity(posts, apps, self.AS_OF, 48)
        self.assertEqual(got["X"], (1, 3), "an application at exactly 48:00 counts, 48:01 does not, "
                                           "and a post with no application is eligible but not filled")
        self.assertEqual(got["all"], (1, 3), "the 'all' key pools every city")

    def test_clock_error(self):
        posts = [post("p1", "2026-10-01 10:00")]
        got = m.post_liquidity(posts, [app("p1", "2026-10-01 09:55")], self.AS_OF, 48)
        self.assertEqual(got["X"], (0, 1), "an application stamped before its post is a clock error, not a fill")
        got = m.post_liquidity(posts, [app("p1", "2026-10-01 09:55"), app("p1", "2026-10-01 10:00")], self.AS_OF, 48)
        self.assertEqual(got["X"], (1, 1), "an application at the second the post went up counts")

    def test_censoring(self):
        posts = [post("old", "2026-10-30 00:00", city="A"), post("young", "2026-10-30 00:01", city="A")]
        got = m.post_liquidity(posts, [app("young", "2026-10-30 05:00")], self.AS_OF, 48)
        self.assertEqual(got["A"], (0, 1), "a post younger than 48 hours at the export is left out, "
                                           "even when it already has an application")
        self.assertEqual(m.post_liquidity([], [], self.AS_OF, 48), {})

    def test_search_success(self):
        posts = [post("p1", "2026-10-05 09:00", "2026-10-05 12:00"),
                 post("p2", "2026-10-06 09:00", ""),
                 post("p3", "2026-10-05 09:00", "", category="other"),
                 post("p4", "2026-10-05 09:00", "", city="Y")]
        searches = [search("2026-10-05 09:00"), search("2026-10-05 12:00"), search("2026-10-05 08:59"),
                    search("2026-10-20 08:00"), search("2026-10-20 08:00", city="Z")]
        got = m.search_success(searches, posts)
        self.assertEqual(got["X"], (2, 4), "open means posted_at <= search < closed_at, a blank closed_at is "
                                           "still open, and only the same city and category count")
        self.assertEqual(got["Z"], (0, 1), "a city with no posts at all: every search finds nothing")
        self.assertEqual(got["all"], (2, 5))
        self.assertEqual(m.search_success([], posts), {})

    def test_diagnose(self):
        liq = {"A": (5, 10), "B": (9, 10), "C": (5, 10), "D": (8, 10), "E": (0, 0), "F": (9, 10)}
        suc = {"A": (10, 10), "B": (1, 10), "C": (1, 10), "D": (8, 10), "E": (5, 10)}
        self.assertEqual(m.diagnose(liq, suc, 0.8),
                         {"A": "workers", "B": "employers", "C": "both", "D": "neither", "E": None, "F": None},
                         "posts waiting means short of workers; searches finding nothing means short of employers; "
                         "exactly the target is fine; no eligible posts or no searches gives None")


class OnDataMixin:
    folder = DATA

    def test_liquidity_and_search(self):
        liq_want, suc_want = reference(self.folder)
        posts, apps, searches = m.load(self.folder)
        liq = m.post_liquidity(posts, apps)
        self.assertEqual(liq, liq_want, "posts filled within 48 hours / eligible posts, by city: expected %s"
                         % liq_want)
        suc = m.search_success(searches, posts)
        self.assertEqual(suc, suc_want, "searches that found an open post, by city: expected %s" % suc_want)

    def test_story(self):
        liq, suc = reference(self.folder)
        posts, apps, searches = m.load(self.folder)
        verdict = m.diagnose(m.post_liquidity(posts, apps), m.search_success(searches, posts))
        self.assertEqual((verdict["Jaipur"], verdict["Kochi"], verdict["Pune"]), ("workers", "employers", "neither"),
                         "Jaipur's posts wait for workers, Kochi's workers wait for posts, Pune is fine")


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
