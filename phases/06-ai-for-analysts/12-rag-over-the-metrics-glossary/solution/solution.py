"""Solution: retrieve glossary entries with BM25, measure recall@k, and check the bot's citations."""
import csv
import math
import os
import re

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
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
    tokens = {d["doc_id"]: tokenize(d["text"]) for d in docs}
    df = {}
    for toks in tokens.values():
        for t in set(toks):
            df[t] = df.get(t, 0) + 1
    n = len(tokens)
    avgdl = sum(len(t) for t in tokens.values()) / n if n else 0.0
    return {"tokens": tokens, "df": df, "n": n, "avgdl": avgdl}


def bm25_score(index, query, doc_id, k1=K1, b=B):
    """BM25 score of one doc for a query. Each distinct query token counts once.

    idf(t)  = ln(1 + (n - df + 0.5) / (df + 0.5))
    part(t) = idf(t) * tf * (k1 + 1) / (tf + k1 * (1 - b + b * doc_length / avgdl))
    """
    toks = index["tokens"][doc_id]
    dl = len(toks)
    score = 0.0
    for t in set(tokenize(query)):
        tf = toks.count(t)
        if tf == 0:
            continue
        df = index["df"][t]
        idf = math.log(1 + (index["n"] - df + 0.5) / (df + 0.5))
        score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / index["avgdl"]))
    return score


def retrieve(index, query, k):
    """Top k (doc_id, score), highest score first, ties broken by doc_id. Docs scoring 0 are left out."""
    scored = [(doc_id, bm25_score(index, query, doc_id)) for doc_id in index["tokens"]]
    scored = [x for x in scored if x[1] > 0]
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored[:k]


def recall_at_k(index, questions, k):
    """Share of questions whose answer_doc_id is in the top k retrieved. 0.0 for no questions."""
    if not questions:
        return 0.0
    hits = sum(1 for q in questions if q["answer_doc_id"] in [d for d, _ in retrieve(index, q["question"], k)])
    return hits / len(questions)


def check_answer(answer, question, glossary):
    """One verdict for a bot answer, checked in this order:

    no_citation     nothing cited
    unknown_id      a cited id is not in the glossary
    deprecated      a cited entry has status deprecated
    wrong_metric    no cited entry is about the metric the question's answer entry defines
    changed_number  a number in the answer is not in any cited entry's text
    ok              none of the above
    """
    by_id = {g["doc_id"]: g for g in glossary}
    cited = [c for c in answer["cited_doc_ids"].split(";") if c.strip()]
    if not cited:
        return "no_citation"
    if any(c not in by_id for c in cited):
        return "unknown_id"
    if any(by_id[c]["status"] == "deprecated" for c in cited):
        return "deprecated"
    wanted = by_id[question["answer_doc_id"]]["metric"]
    if not any(by_id[c]["metric"] == wanted for c in cited):
        return "wrong_metric"
    supported = set()
    for c in cited:
        supported.update(re.findall(r"\d+(?:\.\d+)?", by_id[c]["text"]))
    if any(n not in supported for n in re.findall(r"\d+(?:\.\d+)?", answer["answer"])):
        return "changed_number"
    return "ok"


def audit(answers, questions, glossary):
    """{question_id: verdict} for every answer."""
    qs = {q["question_id"]: q for q in questions}
    return {a["question_id"]: check_answer(a, qs[a["question_id"]], glossary) for a in answers}


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
