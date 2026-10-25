"""Tests for lesson 03: active users and stickiness. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead."""
import csv
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "events.csv")
END = "2026-09-30"
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


def reference(actions=None, start="2026-09-01", end=END):
    """Distinct users per day, and in the date range [start, end]."""
    days, users = {}, set()
    with open(DATA, newline="") as f:
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
        self.assertEqual(m.window("2026-10-01", 2), ["2026-09-30", "2026-10-01"])

    def test_dau_and_window(self):
        self.assertEqual(m.dau(self.by_day, "2026-09-30"), 2)
        self.assertEqual(m.dau(self.by_day, "2026-09-01"), 0)
        self.assertEqual(m.active_in_window(self.by_day, "2026-09-30", 3), 3)
        self.assertEqual(m.active_in_window(self.by_day, "2026-09-30", 1), 2)

    def test_stickiness(self):
        # average DAU = (2 + 1 + 2) / 3, MAU = 3
        self.assertAlmostEqual(m.stickiness(self.by_day, "2026-09-30", days=3), (5 / 3) / 3)
        self.assertEqual(m.stickiness({}, "2026-09-30"), 0.0)


class TestOnData(unittest.TestCase):
    def test_any_event(self):
        days, users = reference()
        by_day = m.active_by_day(DATA)
        self.assertEqual(by_day, days)
        self.assertEqual(m.active_in_window(by_day, END, 30), len(users))
        _, wau = reference(start="2026-09-24")
        self.assertEqual(m.active_in_window(by_day, END, 7), len(wau))
        avg = sum(len(s) for s in days.values()) / 30
        self.assertAlmostEqual(m.stickiness(by_day, END), avg / len(users))

    def test_definition_changes_the_number(self):
        days, users = reference({"log_workout"})
        strict = m.active_by_day(DATA, {"log_workout"})
        self.assertEqual(strict, days)
        loose = m.active_by_day(DATA)
        self.assertEqual(m.active_in_window(strict, END, 30), len(users))
        self.assertLess(m.active_in_window(strict, END, 30), m.active_in_window(loose, END, 30))
        self.assertLess(m.dau(strict, END), m.dau(loose, END))


if __name__ == "__main__":
    unittest.main()
