"""Exercise: score a resume against job postings, from scratch.

SYNONYMS, split_posting, load and main are done for you. Fill in tokenize,
extract_skills, score and rank. Then run: python3 test_lesson.py
"""
import csv
import os
import re

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# canonical skill -> the ways people write it (already lower case, tokens split by spaces)
SYNONYMS = {
    "sql": ["sql", "postgresql", "mysql", "t sql"],
    "python": ["python", "pandas"],
    "r": ["r"],
    "excel": ["excel"],
    "power bi": ["power bi", "powerbi"],
    "tableau": ["tableau"],
    "looker": ["looker"],
    "dbt": ["dbt"],
    "snowflake": ["snowflake"],
    "sas": ["sas"],
    "statistics": ["statistics", "statistical"],
    "a/b testing": ["a/b testing", "a/b tests", "a/b test", "ab testing", "experimentation"],
    "google analytics": ["google analytics", "ga4"],
    "machine learning": ["machine learning"],
}
REQUIRED_WEIGHT = 2
NICE_WEIGHT = 1


def tokenize(text):
    """Lower case word tokens. '/', '+', '#' and '&' between letters stay inside a token: a/b, r&d."""
    # TODO: re.findall on text.lower(). A token is letters and digits, optionally joined
    # by one of / + # & to more letters and digits, so "a/b" and "r&d" are single tokens.
    raise NotImplementedError


def extract_skills(text):
    """Set of canonical skills whose synonym appears as a run of whole tokens."""
    # TODO: join the tokens with spaces, pad both ends with a space, and check
    # " form " for every form in SYNONYMS. Return the set of canonical names.
    raise NotImplementedError


def split_posting(text):
    """(required_text, nice_text). Required is between 'What you need:' and 'Nice to have:'."""
    low = text.lower()
    i = low.find("what you need:")
    j = low.find("nice to have:")
    required = text[i:j] if j > i >= 0 else (text[i:] if i >= 0 else text)
    nice = text[j:] if j >= 0 else ""
    return required, nice


def score(resume_skills, posting_text):
    # TODO: required = skills in the required text, nice = skills in the nice text minus required.
    # score = 100 * (2 * required matched + 1 * nice matched) / (2 * len(required) + len(nice)),
    # rounded to 1 decimal (0.0 if the posting names no skills). Return a dict with keys
    # score, matched_required, missing_required, matched_nice, missing_nice (sorted lists).
    raise NotImplementedError


def rank(resume_text, postings):
    """List of (posting_id, result), best first: score desc, then fewer missing required, then id."""
    # TODO: extract the resume skills once, score every posting, sort.
    raise NotImplementedError


def load(data_dir=DATA):
    with open(os.path.join(data_dir, "resume.txt")) as f:
        resume = f.read()
    with open(os.path.join(data_dir, "postings.csv"), newline="") as f:
        postings = list(csv.DictReader(f))
    return resume, postings


def main():
    resume, postings = load()
    print("resume skills:", sorted(extract_skills(resume)))
    for pid, r in rank(resume, postings):
        print("%s  %5.1f  missing required: %s  missing nice: %s"
              % (pid, r["score"], ", ".join(r["missing_required"]) or "none", ", ".join(r["missing_nice"]) or "none"))


if __name__ == "__main__":
    main()
