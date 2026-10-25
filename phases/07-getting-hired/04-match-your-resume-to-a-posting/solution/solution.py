"""Solution: score a resume against job postings, from scratch."""
import csv
import os
import re

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

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
    return re.findall(r"[a-z0-9]+(?:[/+#&][a-z0-9]+)*", text.lower())


def extract_skills(text):
    """Set of canonical skills whose synonym appears as a run of whole tokens."""
    padded = " " + " ".join(tokenize(text)) + " "
    return {skill for skill, forms in SYNONYMS.items() if any(" %s " % f in padded for f in forms)}


def split_posting(text):
    """(required_text, nice_text). Required is between 'What you need:' and 'Nice to have:'."""
    low = text.lower()
    i = low.find("what you need:")
    j = low.find("nice to have:")
    required = text[i:j] if j > i >= 0 else (text[i:] if i >= 0 else text)
    nice = text[j:] if j >= 0 else ""
    return required, nice


def score(resume_skills, posting_text):
    req_text, nice_text = split_posting(posting_text)
    required = extract_skills(req_text)
    nice = extract_skills(nice_text) - required
    total = REQUIRED_WEIGHT * len(required) + NICE_WEIGHT * len(nice)
    got = REQUIRED_WEIGHT * len(required & resume_skills) + NICE_WEIGHT * len(nice & resume_skills)
    return {
        "score": round(100.0 * got / total, 1) if total else 0.0,
        "matched_required": sorted(required & resume_skills),
        "missing_required": sorted(required - resume_skills),
        "matched_nice": sorted(nice & resume_skills),
        "missing_nice": sorted(nice - resume_skills),
    }


def rank(resume_text, postings):
    """List of (posting_id, result), best first: score desc, then fewer missing required, then id."""
    skills = extract_skills(resume_text)
    rows = [(p["posting_id"], score(skills, p["text"])) for p in postings]
    rows.sort(key=lambda r: (-r[1]["score"], len(r[1]["missing_required"]), r[0]))
    return rows


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
