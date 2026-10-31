"""Solution: why does a search for "data analyst" miss most of the analyst roles at a big company?

normalise_title cleans a raw title, role_family maps it to a role family, and the search
functions measure recall and precision against the generator's labels (SYNTHETIC postings).
The real evidence in data/real_snapshot_2026-10-31.json is read with load_snapshot.
"""
import csv
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
LESSON = os.path.dirname(HERE) if os.path.basename(HERE) == "solution" else HERE
DATA = os.path.join(LESSON, "data")

ABBREVIATIONS = {"sr": "senior", "jr": "junior", "bi": "business intelligence",
                 "bie": "business intelligence engineer", "ops": "operations",
                 "fp&a": "financial planning and analysis"}
LEVEL_WORDS = {"senior", "junior", "lead", "principal", "staff", "i", "ii", "iii", "iv"}
TEAM_SEPARATORS = re.compile(r",| - |\(")

FAMILY_RULES = [
    ("not_analyst", re.compile(r"\bsecurity\b")),
    ("bi", re.compile(r"\bbusiness intelligence\b|\breporting analyst\b")),
    ("product", re.compile(r"\bproduct analyst\b")),
    ("marketing", re.compile(r"\bmarketing analyst\b")),
    ("finance", re.compile(r"\bfinancial analyst\b|\bfinance analyst\b|\bfinancial planning and analysis\b")),
    ("operations", re.compile(r"\boperations analyst\b|\bsupply chain analyst\b|\bplanning analyst\b")),
    ("business", re.compile(r"\bbusiness (systems )?analyst\b")),
    ("data", re.compile(r"\bdata analyst\b|\binsights analyst\b")),
    ("other_analyst", re.compile(r"\banalyst\b")),
]

SYNONYMS = {
    "data": ["data analyst", "insights analyst"],
    "business": ["business analyst", "business systems analyst"],
    "bi": ["business intelligence", "reporting analyst"],
    "finance": ["financial analyst", "finance analyst", "financial planning and analysis"],
    "operations": ["operations analyst", "supply chain analyst", "planning analyst"],
    "product": ["product analyst"],
    "marketing": ["marketing analyst"],
}


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_postings():
    return load_csv(os.path.join(DATA, "postings.csv"))


def load_snapshot():
    with open(os.path.join(DATA, "real_snapshot_2026-10-31.json")) as f:
        return json.load(f)


def normalise_title(raw):
    t = TEAM_SEPARATORS.split((raw or "").lower(), 1)[0]
    words = []
    for token in re.findall(r"[a-z0-9&]+", t):
        words.extend(ABBREVIATIONS.get(token, token).split())
    return " ".join(w for w in words if w not in LEVEL_WORDS)


def role_family(raw):
    t = normalise_title(raw)
    for family, pattern in FAMILY_RULES:
        if pattern.search(t):
            return family
    return "not_analyst"


def naive_search(postings, phrase):
    phrase = phrase.lower()
    return {p["posting_id"] for p in postings if phrase in p["title"].lower()}


def expand(families):
    terms = set()
    for f in families:
        terms.update(SYNONYMS.get(f, []))
    return sorted(terms)


def search(postings, terms):
    patterns = [re.compile(r"\b" + re.escape(t.lower()) + r"\b") for t in terms]
    found = set()
    for p in postings:
        t = normalise_title(p["title"])
        if any(pat.search(t) for pat in patterns):
            found.add(p["posting_id"])
    return found


def measure(found, relevant):
    tp = len(found & relevant)
    return {"tp": tp, "fp": len(found - relevant), "fn": len(relevant - found),
            "recall": None if not relevant else tp / len(relevant),
            "precision": None if not found else tp / len(found)}


def term_costs(postings, relevant, base_terms, extra_terms):
    base = search(postings, base_terms)
    out = []
    for term in extra_terms:
        added = search(postings, [term]) - base
        out.append({"term": term, "added_tp": len(added & relevant), "added_fp": len(added - relevant)})
    return out


if __name__ == "__main__":
    P = load_postings()
    relevant = {r["posting_id"] for r in load_csv(os.path.join(DATA, "labels.csv")) if r["relevant"] == "1"}
    print("naive", measure(naive_search(P, "data analyst"), relevant))
    print("expanded", measure(search(P, expand(SYNONYMS)), relevant))
    print(term_costs(P, relevant, expand(SYNONYMS), ["analyst", "analytics", "data"]))
