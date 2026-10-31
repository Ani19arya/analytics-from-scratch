"""Tests for lesson 04: match your resume to a posting.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

Expected answers come from the skill sets written out by hand below (committed data) or by
the generator (a second dataset built in memory), and are scored in plain Python here.
"""
import csv
import importlib.util
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)

sys.path.insert(0, HERE)
import make_data  # noqa: E402

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
    total = 2 * len(req) + len(nice)
    if total == 0:
        return 0.0
    got = 2 * len(req & skills) + len(nice & skills)
    return round(100.0 * got / total, 1)


def expected_rank(resume_skills, posting_skills):
    rows = [(pid, expected_score(resume_skills, req, nice), len(req - resume_skills))
            for pid, (req, nice) in posting_skills.items()]
    rows.sort(key=lambda r: (-r[1], r[2], r[0]))
    return rows


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
        expected = expected_rank(RESUME_SKILLS, POSTING_SKILLS)
        got = lesson.rank(resume, postings)
        self.assertEqual([g[0] for g in got], [e[0] for e in expected])
        self.assertEqual([g[1]["score"] for g in got], [e[1] for e in expected])

    def test_second_dataset(self):
        for seed in (5, 11, 23):
            data = make_data.build(seed=seed)
            truth = data["truth"]
            postings = [dict(zip(["posting_id", "company", "title", "text"], p)) for p in data["postings"]]
            self.assertEqual(lesson.extract_skills(data["resume"]), truth["resume"],
                             "seed %d: resume skills, written with other spellings" % seed)
            for p in postings:
                req, nice = truth[p["posting_id"]]
                r = lesson.score(truth["resume"], p["text"])
                self.assertEqual(r["score"], expected_score(truth["resume"], req, nice), "seed %d, %s" % (seed, p["posting_id"]))
                self.assertEqual(r["missing_required"], sorted(req - truth["resume"]), "seed %d, %s" % (seed, p["posting_id"]))
                self.assertEqual(r["missing_nice"], sorted(nice - truth["resume"]), "seed %d, %s" % (seed, p["posting_id"]))
            expected = expected_rank(truth["resume"], {pid: truth[pid] for pid in truth if pid != "resume"})
            got = lesson.rank(data["resume"], postings)
            self.assertEqual([(g[0], g[1]["score"]) for g in got], [(e[0], e[1]) for e in expected],
                             "seed %d: ranking by score, then fewer missing required, then id" % seed)


class TestEdgeCases(unittest.TestCase):
    def test_empty_text(self):
        self.assertEqual(lesson.tokenize(""), [], "no text, no tokens")
        self.assertEqual(lesson.extract_skills(""), set(), "no text, no skills")
        r = lesson.score({"sql"}, "")
        self.assertEqual(r["score"], 0.0, "a posting that names no skills scores 0.0, not a division by zero")
        self.assertEqual(r["missing_required"], [])

    def test_empty_resume(self):
        r = lesson.score(set(), "What you need: SQL. Nice to have: Python.")
        self.assertEqual(r["score"], 0.0)
        self.assertEqual(r["missing_required"], ["sql"])
        self.assertEqual(r["missing_nice"], ["python"])

    def test_nice_only_posting(self):
        r = lesson.score({"python"}, "Nice to have: Python, Looker.")
        self.assertEqual(r["score"], 50.0, "no required skills: the score comes from the nice to haves alone")

    def test_tie_breaks(self):
        postings = [{"posting_id": "B", "text": "What you need: SQL, Tableau. Nice to have: Python, Looker."},
                    {"posting_id": "A", "text": "What you need: SQL, Tableau, Excel, Looker. Nice to have: dbt, R."},
                    {"posting_id": "C", "text": "What you need: SQL, Tableau. Nice to have: Python, Looker."},
                    {"posting_id": "Z", "text": "What you need: SQL. Nice to have: Tableau, Looker."}]
        got = [(pid, r["score"]) for pid, r in lesson.rank("SQL and Python", postings)]
        self.assertEqual(got, [("Z", 50.0), ("B", 50.0), ("C", 50.0), ("A", 20.0)],
                         "equal scores are ordered by fewer missing required skills, then by posting id")


if __name__ == "__main__":
    unittest.main()
