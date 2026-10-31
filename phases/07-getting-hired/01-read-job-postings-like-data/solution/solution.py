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

# A number written as digits or as a word from zero to ten.
NUMBER_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
NUM = r"(\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten)"
# "3+ years", "2-4 years", "0 to 2 years", "3-5 yrs", "two years". Not "a 2 year contract".
YEARS = re.compile(r"\b" + NUM + r"\s*(?:(?:-|to)\s*" + NUM + r")?\s*\+?\s*(?:years?|yrs?)\b"
                   r"(?![\s-]*(?:contract|old))", re.I)

# Visa, sentence by sentence. A sentence that mentions sponsoring and has any negation is a
# refusal. A sentence that mentions sponsoring, names a visa and has no negation is a yes.
SPONSOR = re.compile(r"\bsponsor", re.I)
NEGATION = re.compile(r"\b(?:not|no|never|nor|unable|cannot|without|unavailable)\b|n't\b", re.I)
VISA_WORD = re.compile(r"\b(?:visas?|h-?1b|work permits?|immigration|green cards?)\b", re.I)


def load_postings(data_dir=DATA):
    with open(os.path.join(data_dir, "postings.csv"), newline="") as f:
        return list(csv.DictReader(f))


def role_text(text):
    """Drop the company boilerplate: keep everything from 'About the role:' on."""
    i = text.find("About the role:")
    return text if i < 0 else text[i:]


def sentences(text):
    """Split text into sentences at '.', '!' or '?' followed by a space."""
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def extract_tools(text):
    """Sorted list of tool names the role text names anywhere."""
    body = role_text(text)
    return sorted(name for name, pat in TOOL_PATTERNS.items() if pat.search(body))


def extract_asks(text):
    """(required, nice): sorted tool lists from the 'Requirements:' and 'Nice to have:' sentences.
    A tool named in both counts as required only."""
    required, nice = set(), set()
    for s in sentences(role_text(text)):
        if "Requirements:" in s:
            required |= set(extract_tools(s.split("Requirements:", 1)[1]))
        elif "Nice to have:" in s:
            nice |= set(extract_tools(s.split("Nice to have:", 1)[1]))
    return sorted(required), sorted(nice - required)


def to_int(word):
    return int(word) if word.isdigit() else NUMBER_WORDS[word.lower()]


def extract_years(text):
    """(min_years, max_years) from the first experience phrase, max None if open ended. None if absent."""
    m = YEARS.search(role_text(text))
    if not m:
        return None
    lo = to_int(m.group(1))
    hi = to_int(m.group(2)) if m.group(2) else None
    return (lo, hi)


def visa_status(text):
    """'no', 'yes' or 'silent', from the role text only. Refusals are checked first."""
    about = [s for s in sentences(role_text(text)) if SPONSOR.search(s)]
    if any(NEGATION.search(s) for s in about):
        return "no"
    if any(VISA_WORD.search(s) for s in about):
        return "yes"
    return "silent"


def skill_counts(postings, part="required"):
    """{tool: number of postings that ask for it}. part is 'required', 'nice' or 'any'.
    A posting counts once per tool."""
    counts = {}
    for p in postings:
        if part == "any":
            tools = extract_tools(p["text"])
        else:
            required, nice = extract_asks(p["text"])
            tools = required if part == "required" else nice
        for t in tools:
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
    total = len(postings)
    req, nice = skill_counts(postings, "required"), skill_counts(postings, "nice")
    print("postings:", total)
    print("tool      required        nice")
    for t in sorted(req, key=lambda t: (-req[t], t)):
        print("%-9s %4d %5.1f%%  %4d %5.1f%%" % (t, req[t], 100.0 * req[t] / total,
                                               nice.get(t, 0), 100.0 * nice.get(t, 0) / total))
    print(experience_buckets(postings))
    visa = {}
    for p in postings:
        s = visa_status(p["text"])
        visa[s] = visa.get(s, 0) + 1
    print(visa)
    print("learn next if you know SQL and Excel:", learn_next(req, {"SQL", "Excel"}))


if __name__ == "__main__":
    main()
