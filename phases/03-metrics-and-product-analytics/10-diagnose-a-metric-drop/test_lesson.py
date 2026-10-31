"""Tests for lesson 10: diagnose a metric drop. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Every expected number is computed here in plain Python, never read from the solution.
The tests run on the committed data and on a second dataset built with another seed
(where the broken version is on a different platform)."""
import csv
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "daily_users.csv")
BASE, DAY = "2026-10-15", "2026-10-22"
OTHER_SEED = 7
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


def raw(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def row(date, platform, version, city, server, dau):
    return {"date": date, "platform": platform, "app_version": version, "city": city,
            "server_users": server, "dau": dau}


def reference(path):
    """Independent route: one pass over the raw text rows, summing by hand."""
    rows = raw(path)

    def s(date, col, **match):
        return sum(int(r[col]) for r in rows if r["date"] == date and all(r[k] == v for k, v in match.items()))

    dau0, dau1 = s(BASE, "dau"), s(DAY, "dau")
    srv0, srv1 = s(BASE, "server_users"), s(DAY, "server_users")
    keys = sorted({(r["platform"], r["app_version"]) for r in rows if r["date"] == DAY})
    cov = {k: s(DAY, "dau", platform=k[0], app_version=k[1]) / s(DAY, "server_users", platform=k[0], app_version=k[1])
           for k in keys}
    platforms = sorted({r["platform"] for r in rows})
    by_platform = {p: (s(BASE, "dau", platform=p), s(DAY, "dau", platform=p)) for p in platforms}
    return {"dau": (dau0, dau1), "server": (srv0, srv1), "coverage": cov, "by_platform": by_platform}


class TestSmallCases(unittest.TestCase):
    def test_pct_change(self):
        self.assertAlmostEqual(m.pct_change(200, 150), -0.25)
        self.assertIsNone(m.pct_change(0, 10), "a change from 0 has no percentage: return None")
        self.assertEqual(m.pct_change(10, 10), 0.0)

    def test_totals_and_coverage(self):
        rows = [row("d1", "android", "7.3", "Pune", 100, 96), row("d1", "android", "7.4", "Pune", 50, 4),
                row("d1", "web", "web", "Pune", 0, 0), row("d2", "web", "web", "Pune", 10, 10)]
        self.assertEqual(m.totals(rows, "d1"), {(): [100, 150]}, "with no dims the key is the empty tuple")
        self.assertEqual(m.totals(rows, "d1", ("platform",))[("android",)], [100, 150])
        cov = m.coverage(rows, "d1", ("platform", "app_version"))
        self.assertAlmostEqual(cov[("android", "7.4")], 0.08)
        self.assertIsNone(cov[("web", "web")], "no server users: coverage is unknown (None), not 0 or an error")
        self.assertEqual(m.totals(rows, "no such day"), {})

    def test_contributions_order_and_shares(self):
        rows = [row("a", "android", "7.3", "X", 100, 100), row("a", "ios", "7.3", "X", 50, 50),
                row("a", "web", "web", "X", 50, 50),
                row("b", "android", "7.3", "X", 100, 70), row("b", "ios", "7.3", "X", 50, 40),
                row("b", "web", "web", "X", 50, 40)]
        out = m.contributions(rows, "platform", "a", "b")
        self.assertEqual([t[0] for t in out], ["android", "ios", "web"],
                         "biggest fall first, and a tie (ios and web both -10) goes in name order")
        self.assertEqual(out[0][1:4], (100, 70, -30))
        self.assertAlmostEqual(out[0][4], 0.6)
        self.assertAlmostEqual(sum(t[4] for t in out), 1.0, msg="the shares of the change must add up to 1")

    def test_contributions_flat_total(self):
        rows = [row("a", "android", "7.3", "X", 10, 10), row("a", "ios", "7.3", "X", 10, 10),
                row("b", "android", "7.3", "X", 10, 15), row("b", "ios", "7.3", "X", 10, 5)]
        out = m.contributions(rows, "platform", "a", "b")
        self.assertTrue(all(t[4] is None for t in out), "when the total did not move, the shares are None")

    def test_new_segment_in_contributions(self):
        rows = [row("a", "android", "7.3", "X", 10, 10), row("b", "android", "7.3", "X", 4, 4),
                row("b", "android", "7.4", "X", 6, 6)]
        out = dict((t[0], t[1:4]) for t in m.contributions(rows, "app_version", "a", "b"))
        self.assertEqual(out["7.4"], (0, 6, 6), "a value missing on the base date counts as 0 there")

    def test_verdicts(self):
        base = [row("a", "android", "7.3", "X", 1000, 960), row("a", "ios", "7.3", "X", 1000, 960)]
        tracking = base + [row("b", "android", "7.4", "X", 1000, 80), row("b", "ios", "7.3", "X", 1000, 960)]
        d = m.diagnose(tracking, "a", "b")
        self.assertEqual(d["verdict"], "tracking", "DAU fell 46% but server users did not: that is tracking")
        self.assertEqual(d["suspect"], ("android", "7.4"))
        self.assertAlmostEqual(d["dau_change"], (1040 - 1920) / 1920)
        holiday = base + [row("b", "android", "7.3", "X", 800, 768), row("b", "ios", "7.3", "X", 800, 768)]
        d = m.diagnose(holiday, "a", "b")
        self.assertEqual(d["verdict"], "real", "server users fell as much as DAU: the users really stayed away")
        self.assertIsNone(d["suspect"])
        flat = base + [row("b", "android", "7.3", "X", 990, 950), row("b", "ios", "7.3", "X", 1000, 960)]
        self.assertEqual(m.diagnose(flat, "a", "b")["verdict"], "no drop", "a fall under 5% is not a drop")
        self.assertEqual(m.diagnose(base, "z", "a")["verdict"], "no drop",
                         "no data on the base date: nothing to compare, so no drop (not an error)")

    def test_boundary_half(self):
        # DAU -20%, server -10%: exactly half as much is "real"
        base = [row("a", "web", "web", "X", 1000, 1000)]
        d = m.diagnose(base + [row("b", "web", "web", "X", 900, 800)], "a", "b")
        self.assertEqual(d["verdict"], "real", "server fell exactly half as much as DAU: the rule says real")

    def test_corrected_dau(self):
        rows = [row("b", "android", "7.4", "X", 100, 8), row("b", "ios", "7.3", "X", 300, 285),
                row("b", "web", "web", "X", 100, 95)]
        self.assertEqual(m.corrected_dau(rows, "b", ("android", "7.4")), 475,
                         "other segments track 95% of users, so 100 server users on the broken version add 95")
        self.assertEqual(m.corrected_dau(rows, "b", ("ios", "9.9")), 388, "an unknown suspect changes nothing")


class OnDataMixin:
    path = DATA

    def test_diagnosis(self):
        ref = reference(self.path)
        d = m.diagnose(m.load(self.path), BASE, DAY)
        (a, b), (c, e) = ref["dau"], ref["server"]
        self.assertAlmostEqual(d["dau_change"], (b - a) / a, msg="DAU change: expected %+.4f" % ((b - a) / a))
        self.assertAlmostEqual(d["server_change"], (e - c) / c)
        self.assertEqual(d["verdict"], "tracking")
        want = min(ref["coverage"], key=lambda k: (ref["coverage"][k], k))
        self.assertEqual(d["suspect"], want, "the suspect is the platform and version with the lowest coverage")
        self.assertEqual(want[1], "7.4")

    def test_platform_contributions(self):
        ref = reference(self.path)
        out = m.contributions(m.load(self.path), "platform", BASE, DAY)
        total = ref["dau"][1] - ref["dau"][0]
        for value, b, n, change, share in out:
            want = ref["by_platform"][value]
            self.assertEqual((b, n), want, "%s: expected DAU %d -> %d" % (value, want[0], want[1]))
            self.assertAlmostEqual(share, (want[1] - want[0]) / total)
        self.assertEqual(out[0][0], d_suspect_platform(ref), "the broken platform should hold the biggest fall")

    def test_corrected(self):
        ref = reference(self.path)
        rows = raw(self.path)
        suspect = min(ref["coverage"], key=lambda k: (ref["coverage"][k], k))
        ok = [r for r in rows if r["date"] == DAY and (r["platform"], r["app_version"]) != suspect]
        bad = [r for r in rows if r["date"] == DAY and (r["platform"], r["app_version"]) == suspect]
        rate = sum(int(r["dau"]) for r in ok) / sum(int(r["server_users"]) for r in ok)
        want = int(round(sum(int(r["dau"]) for r in ok) + rate * sum(int(r["server_users"]) for r in bad)))
        self.assertEqual(m.corrected_dau(m.load(self.path), DAY, suspect), want)


def d_suspect_platform(ref):
    return min(ref["coverage"], key=lambda k: (ref["coverage"][k], k))[0]


class TestOnData(OnDataMixin, unittest.TestCase):
    pass


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.path = os.path.join(cls.tmp, "daily_users.csv")
        make_data.write_csv(make_data.build(seed=OTHER_SEED)["daily_users"], cls.path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
