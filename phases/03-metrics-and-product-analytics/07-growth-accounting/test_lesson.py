"""Tests for lesson 07: growth accounting. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Every expected number is computed here in plain Python, never read from the solution.
The tests run on the committed data and on a second dataset built with another seed."""
import csv
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "activity.csv")
OTHER_SEED = 5
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


def reference(path):
    """Independent route: a sorted list of each user's active months, then
    label every (user, month) pair by looking at the month before it."""
    months_by_user = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if row["user_id"].strip():
                months_by_user.setdefault(row["user_id"], set()).add(row["session_date"][:7])
    every = sorted(set().union(*months_by_user.values()))
    first, last = every[0], every[-1]
    calendar = []
    y, mo = int(first[:4]), int(first[5:])
    while "%04d-%02d" % (y, mo) <= last:
        calendar.append("%04d-%02d" % (y, mo))
        y, mo = (y + 1, 1) if mo == 12 else (y, mo + 1)
    out = {}
    for i, month in enumerate(calendar):
        before = calendar[i - 1] if i else None
        c = dict(new=0, retained=0, resurrected=0, churned=0, mau=0, prev_mau=0)
        for ms in months_by_user.values():
            first_month = min(ms)
            if month in ms:
                c["mau"] += 1
                if first_month == month:
                    c["new"] += 1
                elif before in ms:
                    c["retained"] += 1
                else:
                    c["resurrected"] += 1
            if before in ms:
                c["prev_mau"] += 1
                if month not in ms:
                    c["churned"] += 1
        out[month] = c
    return calendar, out


KEYS = ("prev_mau", "new", "retained", "resurrected", "churned", "mau")


class TestSmallCases(unittest.TestCase):
    def test_prev_month_and_range(self):
        self.assertEqual(m.prev_month("2026-01"), "2025-12", "January's previous month is December of the year before")
        self.assertEqual(m.prev_month("2026-10"), "2026-09")
        self.assertEqual(m.month_range("2025-11", "2026-02"), ["2025-11", "2025-12", "2026-01", "2026-02"])
        self.assertEqual(m.month_range("2026-03", "2026-03"), ["2026-03"])

    def test_each_label(self):
        # a: new in Jan, retained Feb, churned Mar, resurrected Apr
        # b: new in Feb. c: new in Jan, never back.
        act = {"a": {"2026-01", "2026-02", "2026-04"}, "b": {"2026-02"}, "c": {"2026-01"}}
        feb = m.account(act, "2026-02")
        self.assertEqual((feb["new"], feb["retained"], feb["churned"], feb["resurrected"]), (1, 1, 1, 0))
        apr = m.account(act, "2026-04")
        self.assertEqual(apr["resurrected"], 1,
                         "user a was active in January, so coming back in April is resurrected, not new")
        self.assertEqual(apr["new"], 0, "a user who was ever active before is never new again")
        mar = m.account(act, "2026-03")
        self.assertEqual((mar["mau"], mar["prev_mau"], mar["churned"]), (0, 2, 2))

    def test_gap_month_in_table(self):
        act = {"a": {"2026-01", "2026-03"}}
        table = m.growth_table(act)
        self.assertEqual([r["month"] for r in table], ["2026-01", "2026-02", "2026-03"],
                         "growth_table must include calendar months with no activity")
        self.assertEqual(table[1]["churned"], 1)
        self.assertEqual(table[2]["resurrected"], 1)

    def test_empty(self):
        self.assertEqual(m.growth_table({}), [], "no activity should give an empty table, not an error")

    def test_quick_ratio(self):
        self.assertIsNone(m.quick_ratio({"new": 5, "resurrected": 1, "churned": 0}),
                          "with zero churned users the quick ratio is None, not a division error")
        self.assertAlmostEqual(m.quick_ratio({"new": 6, "resurrected": 3, "churned": 6}), 1.5)
        self.assertEqual(m.quick_ratio({"new": 0, "resurrected": 0, "churned": 4}), 0.0)

    def test_blank_user_and_duplicates(self):
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "a.csv")
            with open(p, "w", newline="") as f:
                f.write("user_id,session_date\n7,2026-02-01\n7,2026-02-20\n,2026-02-03\n 8 ,2026-03-04\n")
            act = m.load_activity(p)
            self.assertEqual(set(act), {"7", "8"}, "skip blank user ids and strip spaces around ids")
            self.assertEqual(act["7"], {"2026-02"}, "two sessions in one month are one active month")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class OnDataMixin:
    path = DATA

    def test_table_matches_reference(self):
        calendar, ref = reference(self.path)
        table = m.growth_table(m.load_activity(self.path))
        self.assertEqual([r["month"] for r in table], calendar)
        for r in table:
            for k in KEYS:
                self.assertEqual(r[k], ref[r["month"]][k],
                                 "%s %s: expected %d, got %d" % (r["month"], k, ref[r["month"]][k], r[k]))

    def test_identity(self):
        for r in m.growth_table(m.load_activity(self.path)):
            self.assertEqual(r["mau"], r["prev_mau"] + r["new"] + r["resurrected"] - r["churned"],
                             "%s: MAU must equal last MAU + new + resurrected - churned" % r["month"])
            self.assertEqual(r["retained"], r["prev_mau"] - r["churned"])

    def test_quick_ratio_on_data(self):
        _, ref = reference(self.path)
        for r in m.growth_table(m.load_activity(self.path)):
            c = ref[r["month"]]
            want = None if c["churned"] == 0 else (c["new"] + c["resurrected"]) / c["churned"]
            got = m.quick_ratio(r)
            if want is None:
                self.assertIsNone(got)
            else:
                self.assertAlmostEqual(got, want, places=9)


class TestOnData(OnDataMixin, unittest.TestCase):
    def test_september_story(self):
        sep = m.account(m.load_activity(self.path), "2026-09")
        self.assertGreater(sep["resurrected"], sep["new"],
                           "in September more lapsed users came back than new users arrived")


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.path = os.path.join(cls.tmp, "activity.csv")
        make_data.write_csv(make_data.build(seed=OTHER_SEED)["activity"], cls.path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
