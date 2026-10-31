"""Tests for lesson 11-04: remote, really.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

Expected classes come from labels written out by hand below (committed data) or from the
generator's truth (second datasets built in memory). Counts are worked out here in plain Python.
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

CLASSES = ["based_in_country", "region_includes", "worldwide", "no_country", "other_country"]
OPEN = {"based_in_country", "region_includes", "worldwide"}

# What a careful reader concludes for someone based in India, by hand.
TRUTH_INDIA = {
    "R01": "based_in_country", "R02": "based_in_country", "R03": "based_in_country",
    "R04": "region_includes", "R05": "worldwide", "R06": "worldwide",
    "R07": "no_country", "R08": "no_country", "R09": "no_country", "R10": "no_country", "R11": "no_country",
    "R12": "other_country", "R13": "other_country", "R14": "other_country", "R15": "other_country",
    "R16": "other_country", "R17": "other_country", "R18": "other_country", "R19": "other_country",
    "R20": "other_country", "R21": "other_country", "R22": "other_country",
}
# Countries each committed other_country posting names, by hand (regions are not countries).
TIED_INDIA = {"R12": ["United States"], "R13": ["United States"], "R14": ["United States"],
              "R15": ["Canada"], "R16": [], "R17": ["United Kingdom"], "R18": [], "R19": [], "R20": [],
              "R21": ["Germany"], "R22": ["Canada"]}


def read(name):
    with open(os.path.join(HERE, "data", name), newline="") as f:
        return list(csv.DictReader(f))


def counts(labels):
    out = {c: 0 for c in CLASSES}
    for v in labels:
        out[v] += 1
    return out


class TestCommitted(unittest.TestCase):
    def setUp(self):
        self.postings, self.places, self.regions = read("remote_postings.csv"), read("places.csv"), read("regions.csv")

    def test_classify(self):
        for p in self.postings:
            self.assertEqual(lesson.classify_location(p["location"], "India", self.places, self.regions),
                             TRUTH_INDIA[p["posting_id"]], "%s: %r for someone in India" % (p["posting_id"], p["location"]))

    def test_summary_and_open(self):
        self.assertEqual(lesson.summary(self.postings, "India", self.places, self.regions), counts(TRUTH_INDIA.values()))
        self.assertEqual(lesson.open_to_me(self.postings, "India", self.places, self.regions),
                         [p["posting_id"] for p in self.postings if TRUTH_INDIA[p["posting_id"]] in OPEN],
                         "open means based in India, a region with India, or worldwide; plain 'Remote' is not open")

    def test_tied_to(self):
        want = {}
        for cs in TIED_INDIA.values():
            for c in cs:
                want[c] = want.get(c, 0) + 1
        self.assertEqual(lesson.tied_to(self.postings, "India", self.places, self.regions), want)

    def test_other_home_same_postings(self):
        got = {p["posting_id"]: lesson.classify_location(p["location"], "United Kingdom", self.places, self.regions)
               for p in self.postings}
        self.assertEqual(got["R17"], "based_in_country", "Remote - UK is based in the United Kingdom")
        self.assertEqual(got["R16"], "region_includes", "EMEA includes the United Kingdom in this lesson's map")
        self.assertEqual(got["R18"], "other_country", "the EU does not include the United Kingdom")
        self.assertEqual(got["R01"], "other_country")
        self.assertEqual(got["R07"], "no_country")


class TestTraps(unittest.TestCase):
    def setUp(self):
        self.places, self.regions = read("places.csv"), read("regions.csv")

    def check(self, location, home, want, why):
        self.assertEqual(lesson.classify_location(location, home, self.places, self.regions), want,
                         "%r for someone in %s: %s" % (location, home, why))

    def test_traps(self):
        self.check("", "India", "no_country", "an empty line names no country")
        self.check("Remote", "India", "no_country", "remote alone is a question, not a yes")
        self.check("Remote - Indianapolis, IN", "India", "other_country", "Indianapolis is in the United States")
        self.check("Remote in Canada", "India", "other_country", "'in' is a word, not India")
        self.check("Remote, anywhere in the United States", "India", "other_country",
                   "a named country beats the word anywhere")
        self.check("Remote, worldwide", "India", "worldwide", "worldwide with no place named")
        self.check("REMOTE (apac)", "India", "region_includes", "case does not matter")
        self.check("Remote - Germany or Poland", "Poland", "based_in_country", "one of the named countries is home")
        self.check("Remote (South Asia)", "Canada", "other_country", "a region without home")

    def test_empty_lists(self):
        self.assertEqual(lesson.summary([], "India", self.places, self.regions), counts([]), "every class with zero")
        self.assertEqual(lesson.open_to_me([], "India", self.places, self.regions), [])
        self.assertEqual(lesson.tied_to([], "India", self.places, self.regions), {})
        self.assertEqual(lesson.named("Remote - India", [], []), (set(), set()), "no map, nothing named")


class TestSecondDataset(unittest.TestCase):
    def test_other_seeds(self):
        for seed in (4, 9, 17):
            d = make_data.build(seed=seed)
            postings = [dict(zip(["posting_id", "company", "title", "location"], p)) for p in d["postings"]]
            places = [dict(zip(["name", "country"], p)) for p in d["places"]]
            regions = [dict(zip(["region", "country"], r)) for r in d["regions"]]
            home, truth = d["home"], d["truth"]
            for p in postings:
                self.assertEqual(lesson.classify_location(p["location"], home, places, regions), truth[p["posting_id"]],
                                 "seed %d, home %s, %s: %r" % (seed, home, p["posting_id"], p["location"]))
            self.assertEqual(lesson.summary(postings, home, places, regions), counts(truth.values()), "seed %d" % seed)
            self.assertEqual(lesson.open_to_me(postings, home, places, regions),
                             [p["posting_id"] for p in postings if truth[p["posting_id"]] in OPEN], "seed %d" % seed)


if __name__ == "__main__":
    unittest.main()
