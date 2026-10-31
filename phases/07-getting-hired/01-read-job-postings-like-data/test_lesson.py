"""Tests for lesson 01: read job postings like data.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

The expected answers come from the generator's labels (data/labels.csv, and a second
dataset built in memory with another seed) and from sentences written by hand here.
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


def read(name):
    with open(os.path.join(HERE, "data", name), newline="") as f:
        return list(csv.DictReader(f))


def as_dicts(header, rows):
    return [dict(zip(header, [str(v) for v in r])) for r in rows]


POSTINGS = read("postings.csv")
LABELS = {r["posting_id"]: r for r in read("labels.csv")}
_p2, _l2 = make_data.build(seed=2468)
POSTINGS_2 = as_dicts(["posting_id", "company", "title", "country", "text"], _p2)
LABELS_2 = {r["posting_id"]: r for r in as_dicts(
    ["posting_id", "tools", "required", "nice", "min_years", "max_years", "visa"], _l2)}


def split(s):
    return sorted(s.split(";")) if s else []


def role(sentence):
    return "About the role: Requirements: SQL. " + sentence


# Refusals. A "yes" on any of these sends a job seeker to a role that will turn them down.
REFUSALS = [
    "Sponsorship is not available for this role.",
    "We are not in a position to sponsor visas.",
    "Candidates must be authorized to work in the US without the need for sponsorship.",
    "We do not offer sponsorship.",
    "We are unable to sponsor work visas for this role.",
    "This role will not sponsor employment visas now or in the future.",
    # not in the lesson data:
    "We cannot sponsor H-1B visas.",
    "Visa sponsorship is unavailable.",
    "We can't provide visa sponsorship now or in the future.",
    "This position is not eligible for visa sponsorship.",
    "No visa sponsorship.",
    "Applicants must be able to work without sponsorship.",
    "We will never sponsor work permits for this role.",
    "Sponsorship won't be offered for this position.",
    "We don't sponsor visas.",
]
GENUINE_YES = [
    "We sponsor H-1B visas for this position.",
    "Visa sponsorship is available for the right candidate.",
    "We can sponsor a Skilled Worker visa.",
    "We are happy to sponsor work permits.",
]
UNCLEAR = [
    "We proudly sponsor local hackathons.",
    "Please state your work authorization status.",
    "Our podcast is sponsored by local shops.",
    "Sponsorship decisions are made case by case.",
    "Benefits: health cover.",
]


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

    def test_empty_text(self):
        self.assertEqual(lesson.extract_tools(""), [], "empty text names no tools")
        self.assertEqual(lesson.extract_asks(""), ([], []), "empty text asks for nothing")
        self.assertIsNone(lesson.extract_years(""), "empty text states no experience")
        self.assertEqual(lesson.visa_status(""), "silent", "empty text says nothing about visas")

    def test_years(self):
        cases = [
            ("0 to 2 years of experience.", (0, 2)),
            ("3+ years of experience.", (3, None)),
            ("2-4 years of experience.", (2, 4)),
            ("At least 5 years of work.", (5, None)),
            ("3-5 yrs of SQL.", (3, 5)),
            ("two years of experience.", (2, None)),
            ("1 year of experience.", (1, None)),
            ("This is a 2 year contract. 3+ years of experience.", (3, None)),
        ]
        for text, want in cases:
            self.assertEqual(lesson.extract_years("About the role: " + text), want, text)
        self.assertIsNone(lesson.extract_years("About the role: a 2 year contract."),
                          "a contract length is not an experience requirement")
        self.assertIsNone(lesson.extract_years("About us: here for 20 years. About the role: Requirements: SQL."),
                          "the company's age is not an experience requirement")

    def test_refusals_are_never_yes(self):
        for s in REFUSALS:
            got = lesson.visa_status(role(s))
            self.assertNotEqual(got, "yes", "a refusal read as yes, the costly error: %r" % s)
            self.assertEqual(got, "no", "this sentence refuses sponsorship: %r" % s)

    def test_genuine_yes_and_unclear(self):
        for s in GENUINE_YES:
            self.assertEqual(lesson.visa_status(role(s)), "yes", "this sentence offers sponsorship: %r" % s)
        for s in UNCLEAR:
            self.assertEqual(lesson.visa_status(role(s)), "silent",
                             "this sentence gives no clear yes or no about visas: %r" % s)

    def test_visa_blurb_is_cut(self):
        text = "About us: We sponsor visas for our touring artists. About the role: Requirements: SQL."
        self.assertEqual(lesson.visa_status(text), "silent", "search the role text, not the company blurb")
        text = "About us: We proudly sponsor the city marathon. About the role: Requirements: SQL."
        self.assertEqual(lesson.visa_status(text), "silent", "search the role text, not the company blurb")

    def test_nice_to_have_is_not_required(self):
        text = "About the role: Requirements: SQL, Python. Nice to have: PowerBI, Python. Reporting matters."
        self.assertEqual(lesson.extract_asks(text), (["Python", "SQL"], ["Power BI"]),
                         "a tool in both lines is required; Power BI is only a nice to have")
        self.assertEqual(lesson.extract_asks("About the role: Requirements: Excel."), (["Excel"], []))


class TestAgainstLabels(unittest.TestCase):
    def check_dataset(self, postings, labels, name):
        bad = []
        for p in postings:
            lab = labels[p["posting_id"]]
            years = None if lab["min_years"] == "" else (int(lab["min_years"]), int(lab["max_years"]) if lab["max_years"] else None)
            got = (lesson.extract_tools(p["text"]), lesson.extract_asks(p["text"]),
                   lesson.extract_years(p["text"]), lesson.visa_status(p["text"]))
            want = (split(lab["tools"]), (split(lab["required"]), split(lab["nice"])), years, lab["visa"])
            if got != want:
                bad.append((p["posting_id"], got, want))
        self.assertEqual(bad[:2], [], "%s: %d postings extracted wrongly; first ones shown as (id, got, expected)"
                         % (name, len(bad)))
        false_yes = [p["posting_id"] for p in postings
                     if labels[p["posting_id"]]["visa"] != "yes" and lesson.visa_status(p["text"]) == "yes"]
        self.assertEqual(false_yes, [], "%s: postings read as visa yes that do not offer sponsorship" % name)

    def check_counts(self, postings, labels, name):
        for part, col in [("required", "required"), ("nice", "nice"), ("any", "tools")]:
            expected = {}
            for lab in labels.values():
                for t in split(lab[col]):
                    expected[t] = expected.get(t, 0) + 1
            self.assertEqual(lesson.skill_counts(postings, part), expected,
                             "%s: skill_counts(part=%r) should count each posting once per tool" % (name, part))
        buckets = lesson.experience_buckets(postings)
        self.assertEqual(set(buckets), {"0-1", "2-3", "4-5", "6+", "not stated"})
        self.assertEqual(sum(buckets.values()), len(postings))
        self.assertEqual(buckets["not stated"], sum(1 for l in labels.values() if l["min_years"] == ""))
        self.assertEqual(buckets["0-1"], sum(1 for l in labels.values() if l["min_years"] in ("0", "1")))

    def test_committed_data(self):
        self.check_dataset(POSTINGS, LABELS, "data/postings.csv")
        self.check_counts(POSTINGS, LABELS, "data/postings.csv")

    def test_second_dataset(self):
        self.check_dataset(POSTINGS_2, LABELS_2, "second dataset (seed 2468)")
        self.check_counts(POSTINGS_2, LABELS_2, "second dataset (seed 2468)")

    def test_empty_and_zero(self):
        self.assertEqual(lesson.skill_counts([]), {}, "no postings, no counts")
        self.assertEqual(lesson.experience_buckets([]), {"0-1": 0, "2-3": 0, "4-5": 0, "6+": 0, "not stated": 0},
                         "every bucket must be present even when it is 0")

    def test_learn_next(self):
        counts = {"SQL": 10, "Python": 7, "Tableau": 7, "Excel": 9, "R": 2}
        self.assertEqual(lesson.learn_next(counts, {"SQL", "Excel"}), ["Python", "Tableau"], "a tie is broken by name")
        self.assertEqual(lesson.learn_next(counts, {"SQL"}, n=1), ["Excel"])
        self.assertEqual(lesson.learn_next({}, {"SQL"}), [], "nothing to learn from an empty count")
        self.assertEqual(lesson.learn_next({"SQL": 3}, {"SQL"}), [], "you already know everything asked for")


if __name__ == "__main__":
    unittest.main()
