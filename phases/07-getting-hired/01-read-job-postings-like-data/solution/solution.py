"""Solution: read job postings like data, with regex and counting."""
import csv
import os
import re

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Tool name -> pattern. Word boundaries stop matches inside other words.
TOOL_PATTERNS = {
    "SQL": re.compile(r"\bSQL\b", re.I),
    "Python": re.compile(r"\bPython\b", re.I),
    "Excel": re.compile(r"\bExcel\b", re.I),
    "Tableau": re.compile(r"\bTableau\b", re.I),
    "Power BI": re.compile(r"\bPower[\s-]?BI\b", re.I),
    # R is one capital letter: case sensitive, a word on its own, and not the R in R&D.
    "R": re.compile(r"(?<![\w&])R(?![\w&])"),
    "Looker": re.compile(r"\bLooker\b", re.I),
    "dbt": re.compile(r"\bdbt\b", re.I),
}

# "3+ years", "2-4 years", "0 to 2 years", "At least 3 years"
YEARS = re.compile(r"(\d+)\s*(?:(?:-|to)\s*(\d+))?\s*\+?\s*years?", re.I)

VISA_NO = re.compile(r"\b(?:unable to|cannot|can't|will not|won't|does not|do not|not able to)\s+sponsor"
                     r"|without (?:visa )?sponsorship|no (?:visa )?sponsorship", re.I)
VISA_YES = re.compile(r"\bsponsor", re.I)


def load_postings(data_dir=DATA):
    with open(os.path.join(data_dir, "postings.csv"), newline="") as f:
        return list(csv.DictReader(f))


def role_text(text):
    """Drop the company boilerplate: keep everything from 'About the role:' on."""
    i = text.find("About the role:")
    return text if i < 0 else text[i:]


def extract_tools(text):
    """Sorted list of tool names the role text asks for."""
    body = role_text(text)
    return sorted(name for name, pat in TOOL_PATTERNS.items() if pat.search(body))


def extract_years(text):
    """(min_years, max_years) from the first experience phrase, max None if open ended. None if absent."""
    m = YEARS.search(role_text(text))
    if not m:
        return None
    lo = int(m.group(1))
    hi = int(m.group(2)) if m.group(2) else None
    return (lo, hi)


def visa_status(text):
    """'no' if it refuses sponsorship, 'yes' if it mentions sponsoring, else 'silent'. Check 'no' first."""
    if VISA_NO.search(text):
        return "no"
    if VISA_YES.search(text):
        return "yes"
    return "silent"


def skill_counts(postings):
    """{tool: number of postings that name it}. A posting counts once per tool."""
    counts = {}
    for p in postings:
        for t in extract_tools(p["text"]):
            counts[t] = counts.get(t, 0) + 1
    return counts


def experience_buckets(postings):
    """Count postings by minimum years asked: '0-1', '2-3', '4-5', '6+', 'not stated'."""
    out = {"0-1": 0, "2-3": 0, "4-5": 0, "6+": 0, "not stated": 0}
    for p in postings:
        y = extract_years(p["text"])
        if y is None:
            out["not stated"] += 1
        elif y[0] <= 1:
            out["0-1"] += 1
        elif y[0] <= 3:
            out["2-3"] += 1
        elif y[0] <= 5:
            out["4-5"] += 1
        else:
            out["6+"] += 1
    return out


def learn_next(counts, known, n=2):
    """The n most requested tools you do not know yet, ties broken by name."""
    todo = [(c, t) for t, c in counts.items() if t not in known]
    todo.sort(key=lambda x: (-x[0], x[1]))
    return [t for _, t in todo[:n]]


def main():
    postings = load_postings()
    counts = skill_counts(postings)
    total = len(postings)
    print("postings:", total)
    for t, c in sorted(counts.items(), key=lambda x: -x[1]):
        print("%-9s %4d  %5.1f%%" % (t, c, 100.0 * c / total))
    print(experience_buckets(postings))
    visa = {}
    for p in postings:
        s = visa_status(p["text"])
        visa[s] = visa.get(s, 0) + 1
    print(visa)
    print("learn next if you know SQL and Excel:", learn_next(counts, {"SQL", "Excel"}))


if __name__ == "__main__":
    main()
