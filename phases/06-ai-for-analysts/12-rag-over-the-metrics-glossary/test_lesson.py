"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py.

BM25 is recomputed here a second way, term by term from posting lists, and the verdict for
every bot answer is checked against the answer key that make_data.build() records when it
plants each problem.
"""
import csv
import importlib.util
import json
import math
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

OTHER_SEED = 1612


def committed(name):
    with open(os.path.join(HERE, "data", name), newline="") as f:
        return list(csv.DictReader(f))


def ref_scores(docs, query, k1=1.5, b=0.75):
    """{doc_id: score} from posting lists: for each query term, walk the docs that contain it."""
    toks = {d["doc_id"]: lesson.tokenize(d["text"]) for d in docs}
    n = len(toks)
    avgdl = sum(len(t) for t in toks.values()) / n
    postings = {}
    for doc_id, ts in toks.items():
        for t in ts:
            postings.setdefault(t, {}).setdefault(doc_id, 0)
            postings[t][doc_id] += 1
    scores = {doc_id: 0.0 for doc_id in toks}
    for term in set(lesson.tokenize(query)):
        plist = postings.get(term, {})
        idf = math.log((n - len(plist) + 0.5 + len(plist) + 0.5) / (len(plist) + 0.5))
        for doc_id, tf in plist.items():
            norm = 1 - b + b * len(toks[doc_id]) / avgdl
            scores[doc_id] += idf * (tf * (k1 + 1)) / (tf + k1 * norm)
    return scores


def ref_top(docs, query, k):
    scores = ref_scores(docs, query)
    ranked = sorted([(d, s) for d, s in scores.items() if s > 0], key=lambda x: (-x[1], x[0]))
    return [d for d, _ in ranked[:k]]


def doc(doc_id, text, metric="m", status="current"):
    return {"doc_id": doc_id, "text": text, "metric": metric, "status": status}


class TestRetrieval(unittest.TestCase):
    def test_tiny_index(self):
        docs = [doc("D1", "apple banana apple"), doc("D2", "banana cherry"), doc("D3", "cherry date fig grape")]
        index = lesson.build_index(docs)
        self.assertEqual(index["n"], 3)
        self.assertEqual(index["df"]["banana"], 2)
        self.assertEqual(index["df"]["apple"], 1, "document frequency counts docs, not occurrences")
        self.assertAlmostEqual(index["avgdl"], 3.0)
        for q in ["apple", "banana cherry", "fig fig fig", "kiwi"]:
            want = ref_scores(docs, q)
            for d in want:
                self.assertAlmostEqual(lesson.bm25_score(index, q, d), want[d], places=9,
                                       msg="BM25 for %r on %s: check idf, tf saturation and length normalisation" % (q, d))

    def test_empty_and_ties(self):
        self.assertEqual(lesson.retrieve(lesson.build_index([]), "anything", 3), [], "an empty glossary retrieves nothing")
        index = lesson.build_index([doc("B2", "late order"), doc("B1", "late order"), doc("C", "refund")])
        self.assertEqual([d for d, _ in lesson.retrieve(index, "late", 5)], ["B1", "B2"],
                         "equal scores are ordered by doc_id, and docs scoring 0 are left out")
        self.assertEqual(lesson.retrieve(index, "kiwi", 5), [])
        self.assertEqual(lesson.recall_at_k(index, [], 3), 0.0)

    def check_glossary(self, glossary, questions, label):
        for docs, name in [(glossary, "all"), ([g for g in glossary if g["status"] == "current"], "current")]:
            index = lesson.build_index(docs)
            for q in questions:
                got = [d for d, _ in lesson.retrieve(index, q["question"], 3)]
                self.assertEqual(got, ref_top(docs, q["question"], 3),
                                 "%s, %s entries: top 3 for %r" % (label, name, q["question"]))
            for k in [1, 3]:
                hits = sum(1 for q in questions if q["answer_doc_id"] in ref_top(docs, q["question"], k))
                self.assertAlmostEqual(lesson.recall_at_k(index, questions, k), hits / len(questions),
                                       msg="%s, %s entries: recall@%d" % (label, name, k))

    def test_committed_retrieval(self):
        glossary, questions = committed("glossary.csv"), committed("questions.csv")
        self.check_glossary(glossary, questions, "committed data")
        everything = lesson.build_index(glossary)
        current = lesson.build_index([g for g in glossary if g["status"] == "current"])
        self.assertLess(lesson.recall_at_k(everything, questions, 1), lesson.recall_at_k(current, questions, 1),
                        "deprecated entries crowd out current ones at rank 1")

    def test_second_dataset_retrieval(self):
        built = make_data.build(seed=OTHER_SEED)
        self.check_glossary(built["glossary"], built["questions"], "seed %d" % OTHER_SEED)


class TestCitations(unittest.TestCase):
    glossary = [doc("G1", "Active user: a completed order in the last 28 days.", "active_user"),
                doc("G2", "Active user: opened the app in the last 30 days.", "active_user", "deprecated"),
                doc("G3", "Late delivery: more than 10 minutes late.", "late_delivery"),
                doc("G4", "Delivery time is the median of 28 orders.", "delivery_time")]
    question = {"question_id": "Q", "question": "What is an active user?", "answer_doc_id": "G1"}

    def verdict(self, text, cited):
        return lesson.check_answer({"question_id": "Q", "answer": text, "cited_doc_ids": cited}, self.question, self.glossary)

    def test_each_verdict(self):
        self.assertEqual(self.verdict("A completed order in the last 28 days.", "G1"), "ok")
        self.assertEqual(self.verdict("A completed order in the last 28 days.", ""), "no_citation")
        self.assertEqual(self.verdict("A completed order in the last 28 days.", " ; "), "no_citation",
                         "blank pieces between separators are not citations")
        self.assertEqual(self.verdict("A completed order in the last 28 days.", "G1;G99"), "unknown_id")
        self.assertEqual(self.verdict("Opened the app in the last 30 days.", "G2"), "deprecated")
        self.assertEqual(self.verdict("Opened the app in the last 30 days.", "G1;G2"), "deprecated",
                         "one deprecated citation is enough to flag the answer")
        self.assertEqual(self.verdict("More than 10 minutes late.", "G3"), "wrong_metric")
        self.assertEqual(self.verdict("A completed order in the last 30 days.", "G1"), "changed_number")
        self.assertEqual(self.verdict("A completed order, no number at all.", "G1"), "ok")

    def test_numbers_from_any_cited_entry(self):
        self.assertEqual(self.verdict("Completed order in 28 days, and 10 minutes.", "G1;G3"), "ok",
                         "a number counts as supported if any cited entry contains it")
        self.assertEqual(self.verdict("Completed order in 28 days.", "G4;G1"), "ok",
                         "the answer cites the right metric among others, so it is not wrong_metric")

    def test_committed_audit(self):
        planted = make_data.build()["planted"]
        got = lesson.audit(committed("bot_answers.csv"), committed("questions.csv"), committed("glossary.csv"))
        for qid, kind in planted.items():
            self.assertEqual(got.get(qid), kind, "committed data %s: expected %s, got %s" % (qid, kind, got.get(qid)))
        self.assertEqual(got["Q01"], "deprecated", "the bot's active user answer cites the deprecated definition")

    def test_second_dataset_audit(self):
        built = make_data.build(seed=OTHER_SEED)
        got = lesson.audit(built["answers"], built["questions"], built["glossary"])
        self.assertEqual(got, built["planted"], "seed %d: verdicts differ from what was planted" % OTHER_SEED)

    def test_fixture(self):
        with open(os.path.join(HERE, "data", "fixture.json")) as f:
            info = json.load(f)
        self.assertEqual(info["answer_source"], "simulated")
        self.assertTrue(info["model"].startswith("none"))


if __name__ == "__main__":
    unittest.main()
