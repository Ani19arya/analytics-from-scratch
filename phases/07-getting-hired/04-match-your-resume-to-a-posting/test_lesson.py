"""Tests for lesson 04: match your resume to a posting.

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

# What a careful human reads in each file, written out by hand.
RESUME_SKILLS = {"sql", "python", "power bi", "excel", "statistics", "a/b testing", "google analytics"}
POSTING_SKILLS = {
    "P1": ({"sql", "power bi", "excel", "statistics"}, {"python", "google analytics"}),
    "P2": ({"sql", "python", "a/b testing", "tableau"}, {"dbt", "looker"}),
    "P3": ({"sas", "sql", "statistics", "excel"}, {"r", "machine learning"}),
    "P4": ({"google analytics", "excel", "power bi"}, {"sql", "a/b testing"}),
    "P5": ({"sql", "python", "snowflake", "dbt", "looker"}, {"power bi", "statistics"}),
}


def load():
    with open(os.path.join(HERE, "data", "resume.txt")) as f:
        resume = f.read()
    with open(os.path.join(HERE, "data", "postings.csv"), newline="") as f:
        return resume, list(csv.DictReader(f))


def expected_score(skills, req, nice):
    got = 2 * len(req & skills) + len(nice & skills)
    return round(100.0 * got / (2 * len(req) + len(nice)), 1)


class TestMatcher(unittest.TestCase):
    def test_tokenize(self):
        self.assertEqual(lesson.tokenize("Power-BI, A/B tests and R&D!"), ["power", "bi", "a/b", "tests", "and", "r&d"])

    def test_synonyms(self):
        for s in ["Power BI", "PowerBI", "Power-BI", "power bi"]:
            self.assertEqual(lesson.extract_skills("Tools: %s." % s), {"power bi"}, s)
        self.assertEqual(lesson.extract_skills("PostgreSQL and pandas"), {"sql", "python"})
        self.assertEqual(lesson.extract_skills("ran A/B tests, read GA4"), {"a/b testing", "google analytics"})

    def test_no_false_matches(self):
        self.assertEqual(lesson.extract_skills("Our R&D team. Reporting to the CFO."), set(),
                         "R&D and Reporting are not the R language")

    def test_resume_and_postings(self):
        resume, postings = load()
        self.assertEqual(lesson.extract_skills(resume), RESUME_SKILLS)
        for p in postings:
            req, nice = POSTING_SKILLS[p["posting_id"]]
            r = lesson.score(RESUME_SKILLS, p["text"])
            self.assertEqual(r["score"], expected_score(RESUME_SKILLS, req, nice), p["posting_id"])
            self.assertEqual(r["matched_required"], sorted(req & RESUME_SKILLS), p["posting_id"])
            self.assertEqual(r["missing_required"], sorted(req - RESUME_SKILLS), p["posting_id"])
            self.assertEqual(r["matched_nice"], sorted(nice & RESUME_SKILLS), p["posting_id"])
            self.assertEqual(r["missing_nice"], sorted(nice - RESUME_SKILLS), p["posting_id"])

    def test_required_weighs_more(self):
        text = "What you need: SQL, Tableau. Nice to have: Python, Looker."
        a = lesson.score({"sql", "tableau"}, text)["score"]
        b = lesson.score({"python", "looker"}, text)["score"]
        self.assertGreater(a, b, "matching the required skills must score higher than matching the nice to haves")
        self.assertEqual(a, 66.7)
        self.assertEqual(b, 33.3)

    def test_rank(self):
        resume, postings = load()
        expected = []
        for pid, (req, nice) in POSTING_SKILLS.items():
            expected.append((pid, expected_score(RESUME_SKILLS, req, nice), len(req - RESUME_SKILLS)))
        expected.sort(key=lambda r: (-r[1], r[2], r[0]))
        got = lesson.rank(resume, postings)
        self.assertEqual([g[0] for g in got], [e[0] for e in expected])
        self.assertEqual([g[1]["score"] for g in got], [e[1] for e in expected])


if __name__ == "__main__":
    unittest.main()
