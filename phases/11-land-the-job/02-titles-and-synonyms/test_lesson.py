"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py.

Expected answers come from the generator's labels, not from a regex: each posting's clean
core title, family and relevance are written by make_data.py when it builds the title. Search
results are recomputed on those core titles with plain word matching, on the committed
postings and on a second set built in memory from another seed.
"""
import csv
import importlib.util
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lesson = load("lesson", TARGET)
make_data = load("make_data", os.path.join(HERE, "make_data.py"))

OTHER_SEED = 2204
NAMED = ["data", "business", "bi", "finance", "operations", "product", "marketing"]


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def has_phrase(core, phrase):
    """Word match without regex: the phrase's words appear in a row in the core title."""
    words, want = core.split(), phrase.lower().split()
    return any(words[i:i + len(want)] == want for i in range(len(words) - len(want) + 1))


def ref_search(labels, terms):
    return {l["posting_id"] for l in labels if any(has_phrase(l["core_title"], t) for t in terms)}


def ref_measure(found, relevant):
    tp = len(found & relevant)
    return tp, len(found - relevant), len(relevant - found)


class TestTitles(unittest.TestCase):
    def test_normalise_by_hand(self):
        cases = {"Senior Financial Analyst, NACF": "financial analyst",
                 "Sr. BI Analyst II": "business intelligence analyst",
                 "BIE III - Ads": "business intelligence engineer",
                 "FP&A Analyst (Retail Finance)": "financial planning and analysis analyst",
                 "  Ops   Analyst ": "operations analyst",
                 "LEAD DATA ANALYST, CUSTOMER INSIGHTS": "data analyst",
                 "Program Manager I, Last Mile Analytics & Quality (LMAQ)": "program manager",
                 "": ""}
        for raw, want in cases.items():
            self.assertEqual(lesson.normalise_title(raw), want,
                             "%r should normalise to %r: lower-case, cut the team name, expand abbreviations, drop level words" % (raw, want))

    def test_family_by_hand(self):
        cases = {"Business Intelligence Engineer II": "bi", "Business Analyst, ROC": "business",
                 "Business Systems Analyst": "business", "Network planning Analyst": "operations",
                 "Security Operations Analyst": "not_analyst", "Security Analyst": "not_analyst",
                 "Pricing Analyst": "other_analyst", "Financial Analyst, GFS FP&A": "finance",
                 "Program Manager I, Last Mile Analytics & Quality (LMAQ)": "not_analyst",
                 "Supply Chain Manager II": "not_analyst", "Insights Analyst": "data",
                 "Product Analyst": "product", "Marketing Analyst": "marketing", "": "not_analyst"}
        for raw, want in cases.items():
            self.assertEqual(lesson.role_family(raw), want, "%r should be %s: check the rule order (security first)" % (raw, want))

    def test_every_generated_title(self):
        for seed in (make_data.DEFAULT_SEED, OTHER_SEED):
            d = make_data.build(seed=seed)
            for p, l in zip(d["postings"], d["labels"]):
                self.assertEqual(lesson.normalise_title(p["title"]), l["core_title"], "seed %d: %r" % (seed, p["title"]))
                self.assertEqual(lesson.role_family(p["title"]), l["family"], "seed %d: %r is %s" % (seed, p["title"], l["family"]))

    def test_real_amazon_titles(self):
        with open(os.path.join(HERE, "data", "real_snapshot_2026-10-31.json")) as f:
            snap = json.load(f)
        fams = [lesson.role_family(t["title"]) for t in snap["amazon"]["top_titles"]]
        self.assertEqual(fams, ["finance", "business", "operations", "not_analyst", "finance", "business", "business", "bi"])
        self.assertNotIn("data", fams, "none of the real top titles is a data analyst title")


class TestSearch(unittest.TestCase):
    def test_naive_and_word_search(self):
        rows = [{"posting_id": "a", "title": "Senior DATA ANALYST"}, {"posting_id": "b", "title": "Big Data Analytics Lead"},
                {"posting_id": "c", "title": "Sr. Ops Analyst, Data Platform"}, {"posting_id": "d", "title": "Database Analyst"}]
        self.assertEqual(lesson.naive_search(rows, "data analyst"), {"a"}, "naive search is a case-blind substring of the raw title")
        self.assertEqual(lesson.naive_search(rows, "data"), {"a", "b", "c", "d"}, "a substring also hits Database and the team name")
        self.assertEqual(lesson.search(rows, ["operations analyst"]), {"c"}, "search runs on the normalised title")
        self.assertEqual(lesson.search(rows, ["data"]), {"a", "b"}, "whole words on the normalised title: Database is not data, and the team name is cut")
        self.assertEqual(lesson.search(rows, []), set())
        self.assertEqual(lesson.search([], ["data analyst"]), set())

    def test_expand(self):
        self.assertEqual(lesson.expand(["product", "marketing"]), ["marketing analyst", "product analyst"])
        self.assertEqual(lesson.expand(["product", "product"]), ["product analyst"], "no repeated terms")
        self.assertEqual(lesson.expand([]), [])
        self.assertEqual(lesson.expand(["nonsense"]), [])

    def test_measure_edges(self):
        m = lesson.measure({"a", "b", "x"}, {"a", "b", "c", "d"})
        self.assertEqual((m["tp"], m["fp"], m["fn"]), (2, 1, 2))
        self.assertAlmostEqual(m["recall"], 0.5)
        self.assertAlmostEqual(m["precision"], 2 / 3.0)
        empty = lesson.measure(set(), {"a"})
        self.assertEqual(empty["recall"], 0)
        self.assertIsNone(empty["precision"], "a search that finds nothing has no precision: return None, not 0 or 1")
        self.assertIsNone(lesson.measure({"a"}, set())["recall"], "with nothing relevant there is no recall: return None")

    def test_term_costs_by_hand(self):
        rows = [{"posting_id": "1", "title": "Financial Analyst"}, {"posting_id": "2", "title": "Pricing Analyst"},
                {"posting_id": "3", "title": "Security Analyst"}, {"posting_id": "4", "title": "Data Entry Specialist"}]
        got = lesson.term_costs(rows, {"1", "2"}, ["financial analyst"], ["analyst", "data", "financial analyst"])
        self.assertEqual(got, [{"term": "analyst", "added_tp": 1, "added_fp": 1},
                               {"term": "data", "added_tp": 0, "added_fp": 1},
                               {"term": "financial analyst", "added_tp": 0, "added_fp": 0}],
                         "count only what each term ADDS to the base search, in the order given")


class TestOnData(unittest.TestCase):
    def check(self, d, label):
        P, L = d["postings"], d["labels"]
        relevant = {l["posting_id"] for l in L if str(l["relevant"]) == "1"}
        naive = lesson.measure(lesson.naive_search(P, "data analyst"), relevant)
        want = {p["posting_id"] for p in P if "data analyst" in p["title"].lower()}
        self.assertEqual((naive["tp"], naive["fp"], naive["fn"]), ref_measure(want, relevant), "%s: naive search" % label)
        terms = lesson.expand(NAMED)
        found = lesson.search(P, terms)
        self.assertEqual(found, ref_search(L, terms), "%s: expanded search" % label)
        exp = lesson.measure(found, relevant)
        self.assertGreater(exp["recall"], naive["recall"] * 5, "%s: the expanded query should find far more relevant roles" % label)
        costs = {c["term"]: c for c in lesson.term_costs(P, relevant, terms, ["analyst", "data"])}
        base = ref_search(L, terms)
        for term in ("analyst", "data"):
            added = ref_search(L, [term]) - base
            self.assertEqual((costs[term]["added_tp"], costs[term]["added_fp"]),
                             (len(added & relevant), len(added - relevant)), "%s: what %r adds" % (label, term))
        self.assertEqual(costs["data"]["added_tp"], 0, "%s: 'data' adds no relevant role here, only noise" % label)

    def test_committed_postings(self):
        d = {"postings": read(os.path.join(HERE, "data", "postings.csv")), "labels": read(os.path.join(HERE, "data", "labels.csv"))}
        self.check(d, "committed postings")

    def test_second_dataset(self):
        self.check(make_data.build(seed=OTHER_SEED), "seed %d" % OTHER_SEED)


if __name__ == "__main__":
    unittest.main()
