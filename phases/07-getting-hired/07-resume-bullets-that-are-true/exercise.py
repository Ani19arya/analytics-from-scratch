"""Exercise: trace every number on a resume to an evidence file.

load, parse_resume, rounds_to and main are done for you.
Fill in extract_claims, candidates, trace and check_resume. Then run: python3 test_lesson.py

Each number in a bullet is a claim. A claim is "ok" when the evidence for that bullet's
project holds a value of the same kind that rounds to it. Otherwise it is:
- "points_as_percent": written with % but it matches a gap in points,
- "inflated": bigger than the nearest evidence value of its kind,
- "understated": smaller than the nearest evidence value of its kind,
- "untraceable": no evidence of its kind for that bullet (or no project at all).
"""
import csv
import os
import re

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
NUMBER = re.compile(r"(?<![\w.,])\d+(?:,\d{3})*(?:\.\d+)?(?!\.?\w)")
HEADING = re.compile(r"\(([a-z0-9-]+)\)\s*$")


def load(data_dir=DATA):
    with open(os.path.join(data_dir, "resume.txt")) as f:
        resume = f.read()
    with open(os.path.join(data_dir, "evidence.csv"), newline="") as f:
        evidence = list(csv.DictReader(f))
    return resume, evidence


def parse_resume(text):
    """[(project id or None, bullet text)], in order. A line ending in "(id)" starts a project;
    any other line that is not a bullet ends it."""
    out, project = [], None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- "):
            out.append((project, line[2:]))
        elif line:
            m = HEADING.search(line)
            project = m.group(1) if m else None
    return out


def extract_claims(bullet):
    """[(number text, kind)] for every number in the bullet. kind is "points" when the number is
    followed by point, points, pts, pp or percentage points; "percent" when followed by % or
    percent; otherwise "number". Commas are removed: "1,400" -> "1400"."""
    # TODO: for each NUMBER match, look at the text after it (lower case, leading spaces removed).
    # Check for points FIRST: "percentage points" also starts with "percent".
    # Hint: re.match(r"(percentage points?|points?|pts|pp)\b", after)
    raise NotImplementedError


def candidates(rows):
    """The values one project's evidence supports, by kind: {"number", "percent", "points"},
    each a list of (value, label)."""
    # TODO: a row with no from_value is one fact: number -> "number", pct -> "percent",
    # pts -> "points". A comparison (from_value filled):
    #   unit number: from, to and abs(to - from) are "number" values
    #   unit pct: from and to are "percent" values, abs(to - from) is a "points" value
    #   either unit: abs(to - from) / from * 100 is a "percent" value (the relative change),
    #   unless from is 0.
    # Each value goes in as (float value, a label saying where it came from).
    raise NotImplementedError


def rounds_to(value, text):
    """True when value rounded to the decimals written in text gives text: 34.6 -> "35" is True."""
    places = len(text.split(".")[1]) if "." in text else 0
    return abs(value - float(text)) <= 0.5 * 10 ** -places + 1e-9


def trace(text, kind, cands):
    """(status, evidence value or None) for one claim against one project's candidates."""
    # TODO, in this order:
    # 1. any candidate of the same kind that rounds_to(value, text): ("ok", value)
    # 2. a percent claim that rounds to a points candidate: ("points_as_percent", value)
    # 3. no candidates of the same kind: ("untraceable", None)
    # 4. the nearest candidate of the same kind (ties: the smaller value):
    #    ("inflated", nearest) if the claim is bigger, else ("understated", nearest)
    raise NotImplementedError


def check_resume(resume_text, evidence_rows):
    """One finding per claim: {"bullet": 1-based bullet number, "project", "claim", "kind",
    "status", "evidence"}."""
    # TODO: group the evidence rows by project, then for every bullet from parse_resume
    # (numbered from 1) and every claim in it, trace the claim against that project's
    # candidates. A bullet with no project, or a project with no evidence, has no candidates.
    raise NotImplementedError


def main():
    resume, evidence = load()
    for f in check_resume(resume, evidence):
        ev = "" if f["evidence"] is None else "  evidence %.2f" % f["evidence"]
        print("bullet %d  %-8s %-8s %s%s" % (f["bullet"], f["claim"], f["kind"], f["status"], ev))


if __name__ == "__main__":
    main()
