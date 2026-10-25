"""Tests for lesson 03: portfolio project end to end.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py
"""
import csv
import datetime
import importlib.util
import math
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)

AS_OF = datetime.date(2026, 10, 1)
SECTIONS = ["Question", "Data", "Method", "Result", "Recommendation", "Limitations"]


def expected_groups():
    out = {}
    with open(os.path.join(HERE, "data", "subscriptions.csv"), newline="") as f:
        for r in csv.DictReader(f):
            signup = datetime.date.fromisoformat(r["signup_date"])
            if (AS_OF - signup).days < 90:
                continue
            churned = bool(r["cancel_date"]) and (datetime.date.fromisoformat(r["cancel_date"]) - signup).days <= 90
            n, c = out.get(r["start_type"], (0, 0))
            out[r["start_type"]] = (n + 1, c + int(churned))
    return out


class TestPortfolio(unittest.TestCase):
    def test_pull(self):
        got = lesson.pull(lesson.load_db())
        self.assertEqual(got, expected_groups(),
                         "keep only customers with 90 days of history, and count cancels within 90 days of signup")

    def test_two_proportion_test(self):
        t = lesson.two_proportion_test(60, 200, 40, 200)
        self.assertAlmostEqual(t["diff"], 0.10, places=9)
        pooled = 0.25
        z = 0.10 / math.sqrt(pooled * 0.75 * (2 / 200))
        self.assertAlmostEqual(t["z"], z, places=6)
        self.assertAlmostEqual(t["p_value"], math.erfc(z / math.sqrt(2)), places=6)
        se = math.sqrt(0.3 * 0.7 / 200 + 0.2 * 0.8 / 200)
        self.assertAlmostEqual(t["ci_low"], 0.10 - 1.96 * se, places=6)
        self.assertAlmostEqual(t["ci_high"], 0.10 + 1.96 * se, places=6)
        same = lesson.two_proportion_test(50, 200, 50, 200)
        self.assertAlmostEqual(same["z"], 0.0)
        self.assertAlmostEqual(same["p_value"], 1.0)

    def test_write_up(self):
        g = expected_groups()
        t = lesson.two_proportion_test(g["trial"][1], g["trial"][0], g["paid"][1], g["paid"][0])
        text = lesson.write_up(g, t)
        heads = re.findall(r"^## (.+)$", text, re.M)
        self.assertEqual(heads, SECTIONS, "the write-up needs these sections, in this order")
        for n, c in g.values():
            self.assertIn("%d of %d" % (c, n), text, "the Result section should give counts, not only percentages")
        self.assertIn("%.1f%%" % (100 * t["p1"]), text)
        self.assertIn("%.1f%%" % (100 * t["p2"]), text)
        limits = text.split("## Limitations", 1)[1]
        self.assertGreaterEqual(limits.count("\n- "), 2, "list at least two limitations")
        self.assertRegex(limits.lower(), r"experiment|observational|causal", "say that this comparison is not an experiment")
        self.assertLess(len(text.split()), 450, "one page: keep it short")


if __name__ == "__main__":
    unittest.main()
