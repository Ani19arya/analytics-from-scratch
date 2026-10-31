"""Solution: trace every number on a resume to an evidence file.

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

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
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
    claims = []
    for m in NUMBER.finditer(bullet):
        after = bullet[m.end():].lower().lstrip()
        if re.match(r"(percentage points?|points?|pts|pp)\b", after):
            kind = "points"
        elif after.startswith("%") or re.match(r"percent\b", after):
            kind = "percent"
        else:
            kind = "number"
        claims.append((m.group().replace(",", ""), kind))
    return claims


def candidates(rows):
    """The values one project's evidence supports, by kind: {"number", "percent", "points"},
    each a list of (value, label)."""
    out = {"number": [], "percent": [], "points": []}
    for r in rows:
        unit, metric = r["unit"], r["metric"]
        to = float(r["to_value"])
        if not r["from_value"]:
            kind = {"number": "number", "pct": "percent", "pts": "points"}[unit]
            out[kind].append((to, metric))
            continue
        frm = float(r["from_value"])
        if unit == "number":
            out["number"] += [(frm, metric + " (from)"), (to, metric + " (to)"), (abs(to - frm), metric + " (change)")]
        elif unit == "pct":
            out["percent"] += [(frm, metric + " (from)"), (to, metric + " (to)")]
            out["points"].append((abs(to - frm), metric + " (change in points)"))
        if frm != 0:
            out["percent"].append((abs(to - frm) / frm * 100, metric + " (relative change)"))
    return out


def rounds_to(value, text):
    """True when value rounded to the decimals written in text gives text: 34.6 -> "35" is True."""
    places = len(text.split(".")[1]) if "." in text else 0
    return abs(value - float(text)) <= 0.5 * 10 ** -places + 1e-9


def trace(text, kind, cands):
    """(status, evidence value or None) for one claim against one project's candidates."""
    same = cands[kind]
    for value, _ in same:
        if rounds_to(value, text):
            return ("ok", value)
    if kind == "percent":
        for value, _ in cands["points"]:
            if rounds_to(value, text):
                return ("points_as_percent", value)
    if not same:
        return ("untraceable", None)
    claimed = float(text)
    nearest = min(same, key=lambda c: (abs(c[0] - claimed), c[0]))[0]
    return ("inflated", nearest) if claimed > nearest else ("understated", nearest)


def check_resume(resume_text, evidence_rows):
    """One finding per claim: {"bullet": 1-based bullet number, "project", "claim", "kind",
    "status", "evidence"}."""
    by_project = {}
    for r in evidence_rows:
        by_project.setdefault(r["project"], []).append(r)
    empty = {"number": [], "percent": [], "points": []}
    findings = []
    for i, (project, bullet) in enumerate(parse_resume(resume_text), 1):
        cands = candidates(by_project[project]) if project in by_project else empty
        for text, kind in extract_claims(bullet):
            status, value = trace(text, kind, cands)
            findings.append({"bullet": i, "project": project, "claim": text, "kind": kind,
                             "status": status, "evidence": value})
    return findings


def main():
    resume, evidence = load()
    for f in check_resume(resume, evidence):
        ev = "" if f["evidence"] is None else "  evidence %.2f" % f["evidence"]
        print("bullet %d  %-8s %-8s %s%s" % (f["bullet"], f["claim"], f["kind"], f["status"], ev))


if __name__ == "__main__":
    main()
