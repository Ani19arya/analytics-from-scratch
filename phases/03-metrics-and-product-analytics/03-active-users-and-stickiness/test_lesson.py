"""Tests for lesson 03: active users and stickiness. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Expected answers are computed here in plain Python from the raw rows. The checks run
on the committed data, on a second dataset built with another seed, and on small
hand-made cases (an empty log, an empty definition, a five-user week)."""
import csv
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "events.csv")
END = "2026-09-30"
OTHER_SEED = 11
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


def reference(path, actions=None, start="2026-09-01", end=END):
    """Distinct users per day, and in the date range [start, end]."""
    days, users = {}, set()
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if actions is not None and row["event_name"] not in actions:
                continue
            uid = int(row["user_id"])
            days.setdefault(row["event_date"], set()).add(uid)
            if start <= row["event_date"] <= end:
                users.add(uid)
    return days, users


class TestToy(unittest.TestCase):
    def setUp(self):
        self.by_day = {"2026-09-28": {1, 2}, "2026-09-29": {1}, "2026-09-30": {1, 3}}

    def test_window(self):
        self.assertEqual(m.window("2026-09-30", 3), ["2026-09-28", "2026-09-29", "2026-09-30"])
        self.assertEqual(m.window("2026-10-01", 2), ["2026-09-30", "2026-10-01"], "the window must cross a month end")
        self.assertEqual(m.window("2026-09-30", 1), ["2026-09-30"])

    def test_dau_and_window(self):
        self.assertEqual(m.dau(self.by_day, "2026-09-30"), 2)
        self.assertEqual(m.dau(self.by_day, "2026-09-01"), 0, "a day with nobody active is 0, not an error")
        self.assertEqual(m.active_in_window(self.by_day, "2026-09-30", 3), 3)
        self.assertEqual(m.active_in_window(self.by_day, "2026-09-30", 1), 2)

    def test_stickiness(self):
        # average DAU = (2 + 1 + 2) / 3, MAU = 3
        self.assertAlmostEqual(m.stickiness(self.by_day, "2026-09-30", days=3), (5 / 3) / 3)
        self.assertEqual(m.stickiness({}, "2026-09-30"), 0.0, "nobody active: stickiness is 0.0, not a division error")

    def test_five_user_week(self):
        # The grid in the README: user 1 every day, user 2 every other day, user 3 once,
        # user 4 on the last two days, user 5 not at all this week.
        by_day = {}
        marks = {1: range(24, 31), 2: (24, 26, 28, 30), 3: (25,), 4: (29, 30), 5: ()}
        for uid, days in marks.items():
            for d in days:
                by_day.setdefault("2026-09-%02d" % d, set()).add(uid)
        week = ["2026-09-%02d" % d for d in range(24, 31)]
        self.assertEqual(sum(m.dau(by_day, d) for d in week), 14)
        self.assertEqual(m.active_in_window(by_day, "2026-09-30", 7), 4,
                         "WAU is the union of the daily sets (4 users), not the sum of DAU (14)")
        self.assertAlmostEqual(m.stickiness(by_day, "2026-09-30", days=7), 2.0 / 4)


class TestActiveByDayEdges(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, rows):
        path = os.path.join(self.tmp, "events.csv")
        make_data.write_csv(rows, path)
        return path

    def test_empty_log(self):
        self.assertEqual(m.active_by_day(self.write([])), {}, "an empty log has no active days")

    def test_empty_definition_is_not_any_event(self):
        path = self.write([{"user_id": 1, "event_date": "2026-09-30", "event_name": "app_open"}])
        self.assertEqual(m.active_by_day(path, set()), {},
                         "actions=set() means no event counts; only actions=None means any event")
        self.assertEqual(m.active_by_day(path), {"2026-09-30": {1}}, "user_id must be an int")


class OnDataChecks:
    def test_any_event(self):
        days, users = reference(self.path)
        by_day = m.active_by_day(self.path)
        self.assertEqual(by_day, days)
        self.assertEqual(m.active_in_window(by_day, END, 30), len(users))
        _, wau = reference(self.path, start="2026-09-24")
        self.assertEqual(m.active_in_window(by_day, END, 7), len(wau))
        avg = sum(len(s) for s in days.values()) / 30
        self.assertAlmostEqual(m.stickiness(by_day, END), avg / len(users))

    def test_definition_changes_the_number(self):
        days, users = reference(self.path, {"log_workout"})
        strict = m.active_by_day(self.path, {"log_workout"})
        self.assertEqual(strict, days)
        loose = m.active_by_day(self.path)
        self.assertEqual(m.active_in_window(strict, END, 30), len(users))
        _, wau = reference(self.path, {"log_workout"}, start="2026-09-24")
        self.assertEqual(m.active_in_window(strict, END, 7), len(wau))
        self.assertLess(m.active_in_window(strict, END, 30), m.active_in_window(loose, END, 30))
        self.assertLessEqual(m.dau(strict, END), m.dau(loose, END))


class TestOnData(OnDataChecks, unittest.TestCase):
    path = DATA


class TestOnSecondDataset(OnDataChecks, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.path = os.path.join(cls.tmp, "events.csv")
        make_data.write_csv(make_data.build(seed=OTHER_SEED)["events"], cls.path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
