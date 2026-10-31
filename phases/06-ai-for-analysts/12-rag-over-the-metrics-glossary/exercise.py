"""Exercise: retrieve glossary entries with BM25, measure recall@k, and check the bot's citations.

tokenize is given. Fill in the functions marked TODO. Then run: python3 test_lesson.py
"""
import csv
import math
import os
import re

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
K1 = 1.5
B = 0.75
STOPWORDS = {"a", "an", "the", "is", "are", "of", "in", "on", "to", "do", "we", "our", "how", "what", "who",
             "when", "as", "by", "for", "and", "or", "it", "its", "be", "with", "that", "this", "does", "much", "many"}


def load_csv(name):
    with open(os.path.join(DATA, name), newline="") as f:
        return list(csv.DictReader(f))


def tokenize(text):
    """Lower case words and numbers, without stopwords. 'AOV' and 'aov' are the same token."""
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOPWORDS]


def build_index(docs):
    """BM25 index over docs (dicts with doc_id and text): tokens per doc, document frequency, average length.

    Return {"tokens": {doc_id: [tokens]}, "df": {token: number of docs containing it},
    "n": number of docs, "avgdl": average number of tokens per doc (0.0 when there are no docs)}.
    """
    # TODO
    raise NotImplementedError


def bm25_score(index, query, doc_id, k1=K1, b=B):
    """BM25 score of one doc for a query. Each distinct query token counts once.

    idf(t)  = ln(1 + (n - df + 0.5) / (df + 0.5))
    part(t) = idf(t) * tf * (k1 + 1) / (tf + k1 * (1 - b + b * doc_length / avgdl))
    """
    # TODO
    raise NotImplementedError


def retrieve(index, query, k):
    """Top k (doc_id, score), highest score first, ties broken by doc_id. Docs scoring 0 are left out."""
    # TODO
    raise NotImplementedError


def recall_at_k(index, questions, k):
    """Share of questions whose answer_doc_id is in the top k retrieved. 0.0 for no questions."""
    # TODO
    raise NotImplementedError


def check_answer(answer, question, glossary):
    """One verdict for a bot answer, checked in this order:

    no_citation     nothing cited
    unknown_id      a cited id is not in the glossary
    deprecated      a cited entry has status deprecated
    wrong_metric    no cited entry is about the metric the question's answer entry defines
    changed_number  a number in the answer is not in any cited entry's text
    ok              none of the above
    """
    # TODO
    raise NotImplementedError


def audit(answers, questions, glossary):
    """{question_id: verdict} for every answer."""
    # TODO
    raise NotImplementedError


def main():
    glossary = load_csv("glossary.csv")
    questions = load_csv("questions.csv")
    answers = load_csv("bot_answers.csv")
    everything = build_index(glossary)
    current = build_index([g for g in glossary if g["status"] == "current"])
    for k in [1, 3]:
        print("recall@%d all entries %.2f, current only %.2f" % (
            k, recall_at_k(everything, questions, k), recall_at_k(current, questions, k)))
    verdicts = audit(answers, questions, glossary)
    for qid, verdict in verdicts.items():
        if verdict != "ok":
            print(qid, verdict)
    print("ok:", sum(v == "ok" for v in verdicts.values()), "of", len(verdicts))


if __name__ == "__main__":
    main()
