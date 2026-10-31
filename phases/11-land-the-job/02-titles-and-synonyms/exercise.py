"""Exercise: why does a search for "data analyst" miss most of the analyst roles at a big company?

normalise_title cleans a raw title, role_family maps it to a role family, and the search
functions measure recall and precision against the generator's labels (SYNTHETIC postings).
The real evidence in data/real_snapshot_2026-10-31.json is read with load_snapshot.

Fill in FAMILY_RULES and every function marked TODO. Then run: python3 test_lesson.py
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

# TODO: (family, compiled regex) pairs, checked in order on the NORMALISED title; the first
# match wins, and a title that matches nothing is "not_analyst". The families and the phrases
# that mark them, in ALPHABETICAL order (not the order your rules need):
#   bi: "business intelligence" or "reporting analyst"
#   business: "business analyst" or "business systems analyst"
#   data: "data analyst" or "insights analyst"
#   finance: "financial analyst", "finance analyst" or "financial planning and analysis"
#   marketing: "marketing analyst"
#   not_analyst: the word "security" (security analysts are not the analyst work we want)
#   operations: "operations analyst", "supply chain analyst" or "planning analyst"
#   other_analyst: any other title with the word "analyst"
#   product: "product analyst"
# Use word edges (\b). Decide which rules must come before which, and why.
FAMILY_RULES = []

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
    """Return the core title: lower-case; cut everything from the first comma, " - " or "("
    (that is the team name); split into words of letters, digits and &; expand each word with
    ABBREVIATIONS; drop LEVEL_WORDS; join with single spaces. None or "" gives ""."""
    # TODO
    raise NotImplementedError


def role_family(raw):
    """The family of the first rule in FAMILY_RULES that matches normalise_title(raw),
    or "not_analyst"."""
    # TODO
    raise NotImplementedError


def naive_search(postings, phrase):
    """posting_ids whose RAW title contains the phrase, ignoring case. This is the search
    most people type."""
    # TODO
    raise NotImplementedError


def expand(families):
    """Sorted list of the SYNONYMS terms for the given families, each term once.
    Unknown families add nothing."""
    # TODO
    raise NotImplementedError


def search(postings, terms):
    """posting_ids whose NORMALISED title contains any term as whole words."""
    # TODO
    raise NotImplementedError


def measure(found, relevant):
    """Return {"tp", "fp", "fn", "recall", "precision"} for a set of found ids and a set of
    relevant ids. recall = tp / relevant (None if nothing is relevant); precision = tp / found
    (None if nothing was found)."""
    # TODO
    raise NotImplementedError


def term_costs(postings, relevant, base_terms, extra_terms):
    """For each extra term, in order: {"term", "added_tp", "added_fp"}, counting only the
    postings the term finds that search(postings, base_terms) did not already find."""
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    P = load_postings()
    relevant = {r["posting_id"] for r in load_csv(os.path.join(DATA, "labels.csv")) if r["relevant"] == "1"}
    print("naive", measure(naive_search(P, "data analyst"), relevant))
    print("expanded", measure(search(P, expand(SYNONYMS)), relevant))
    print(term_costs(P, relevant, expand(SYNONYMS), ["analyst", "analytics", "data"]))
