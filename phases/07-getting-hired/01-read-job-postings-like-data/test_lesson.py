"""Tests for lesson 01: read job postings like data.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py
"""
import csv
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)


def read(name):
    with open(os.path.join(HERE, "data", name), newline="") as f:
        return list(csv.DictReader(f))


POSTINGS = read("postings.csv")
LABELS = {r["posting_id"]: r for r in read("labels.csv")}


class TestTraps(unittest.TestCase):
    def test_excel_in_boilerplate(self):
        text = "About us: Our teams excel at service. About the role: Requirements: SQL."
        self.assertEqual(lesson.extract_tools(text), ["SQL"], "the verb 'excel' in the company blurb is not the tool")

    def test_r_inside_words(self):
        text = "About the role: support our R&D team. Requirements: Tableau. Reporting skills matter."
        self.assertEqual(lesson.extract_tools(text), ["Tableau"], "R inside Reporting or R&D is not the R language")
        self.assertEqual(lesson.extract_tools("About the role: Requirements: R or Python."), ["Python", "R"])

    def test_power_bi_spellings(self):
        for s in ["Power BI", "PowerBI", "Power-BI", "power bi"]:
            self.assertEqual(lesson.extract_tools("About the role: Requirements: %s." % s), ["Power BI"], s)

    def test_years(self):
        self.assertEqual(lesson.extract_years("About the role: 0 to 2 years of experience."), (0, 2))
        self.assertEqual(lesson.extract_years("About the role: 3+ years of experience."), (3, None))
        self.assertEqual(lesson.extract_years("About the role: 2-4 years of experience."), (2, 4))
        self.assertEqual(lesson.extract_years("About the role: At least 5 years of work."), (5, None))
        self.assertIsNone(lesson.extract_years("About us: here for 20 years. About the role: Requirements: SQL."),
                          "the company's age is not an experience requirement")

    def test_visa(self):
        self.assertEqual(lesson.visa_status("This role will not sponsor employment visas."), "no")
        self.assertEqual(lesson.visa_status("Must be authorized to work without visa sponsorship."), "no")
        self.assertEqual(lesson.visa_status("We sponsor H-1B visas for this position."), "yes")
        self.assertEqual(lesson.visa_status("Benefits: health cover."), "silent")


class TestAgainstLabels(unittest.TestCase):
    def test_every_posting(self):
        bad = []
        for p in POSTINGS:
            lab = LABELS[p["posting_id"]]
            tools = sorted(lab["tools"].split(";"))
            years = None if lab["min_years"] == "" else (int(lab["min_years"]), int(lab["max_years"]) if lab["max_years"] else None)
            got = (lesson.extract_tools(p["text"]), lesson.extract_years(p["text"]), lesson.visa_status(p["text"]))
            if got != (tools, years, lab["visa"]):
                bad.append((p["posting_id"], got, (tools, years, lab["visa"])))
        self.assertEqual(bad[:3], [], "%d postings extracted wrongly; first ones shown as (id, got, expected)" % len(bad))

    def test_counts_and_buckets(self):
        counts = lesson.skill_counts(POSTINGS)
        expected = {}
        for lab in LABELS.values():
            for t in lab["tools"].split(";"):
                expected[t] = expected.get(t, 0) + 1
        self.assertEqual(counts, expected)
        buckets = lesson.experience_buckets(POSTINGS)
        self.assertEqual(set(buckets), {"0-1", "2-3", "4-5", "6+", "not stated"})
        self.assertEqual(sum(buckets.values()), len(POSTINGS))
        self.assertEqual(buckets["not stated"], sum(1 for l in LABELS.values() if l["min_years"] == ""))
        self.assertEqual(buckets["0-1"], sum(1 for l in LABELS.values() if l["min_years"] in ("0", "1")))

    def test_learn_next(self):
        counts = {"SQL": 10, "Python": 7, "Tableau": 7, "Excel": 9, "R": 2}
        self.assertEqual(lesson.learn_next(counts, {"SQL", "Excel"}), ["Python", "Tableau"])
        self.assertEqual(lesson.learn_next(counts, {"SQL"}, n=1), ["Excel"])


if __name__ == "__main__":
    unittest.main()
