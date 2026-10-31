"""Exercise: read job postings like data, with regex and counting.

load_postings, role_text, sentences, to_int and main are done for you.
Fill in everything marked TODO. Then run: python3 test_lesson.py
"""
import csv
import os
import re

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# TODO: one compiled pattern per tool. Use word boundaries (\b) so a tool name does not
# match inside another word. Watch three cases:
#   Power BI is also written PowerBI and Power-BI.
#   R is one capital letter: case sensitive, a word on its own, and not the R in R&D.
#   Excel is fine case insensitive once the company blurb is removed (see role_text).
TOOL_PATTERNS = {
    "SQL": None,
    "Python": None,
    "Excel": None,
    "Tableau": None,
    "Power BI": None,
    "R": None,
    "Looker": None,
    "dbt": None,
}

# A number written as digits or as a word from zero to ten. Done for you.
NUMBER_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
NUM = r"(\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten)"

# TODO: match "3+ years", "2-4 years", "0 to 2 years", "At least 3 years", "3-5 yrs" and
# "two years", but not "a 2 year contract". Group 1 is the low number, group 2 the high
# number (absent for open ended). Build it from NUM, compile it with re.I.
# Hint: (?:years?|yrs?)\b for the unit, and a negative lookahead (?!...) for "contract".
YEARS = None

# TODO: three patterns for visa_status.
# SPONSOR finds any form of the word: sponsor, sponsors, sponsorship, sponsoring.
# NEGATION finds a negation word: not, no, never, nor, unable, cannot, without,
#   unavailable, and any word ending in n't (don't, can't, won't).
# VISA_WORD finds a visa word: visa, visas, H-1B, H1B, work permit, immigration, green card.
SPONSOR = None
NEGATION = None
VISA_WORD = None


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


def to_int(word):
    return int(word) if word.isdigit() else NUMBER_WORDS[word.lower()]


def extract_tools(text):
    """Sorted list of tool names the role text names anywhere."""
    # TODO: search role_text(text) with each pattern in TOOL_PATTERNS.
    raise NotImplementedError


def extract_asks(text):
    """(required, nice): sorted tool lists from the 'Requirements:' and 'Nice to have:' sentences.
    A tool named in both counts as required only."""
    # TODO: loop over sentences(role_text(text)). A sentence that contains "Requirements:"
    # adds the tools after that marker to required; one with "Nice to have:" adds to nice.
    raise NotImplementedError


def extract_years(text):
    """(min_years, max_years) from the first experience phrase, max None if open ended. None if absent."""
    # TODO: search role_text(text) with YEARS, turn the groups into ints with to_int.
    raise NotImplementedError


def visa_status(text):
    """'no', 'yes' or 'silent', from the role text only. Refusals are checked first."""
    # TODO: keep the sentences of role_text(text) that mention sponsoring.
    # Any of them has a negation: "no". Else any of them names a visa: "yes". Else "silent".
    raise NotImplementedError


def skill_counts(postings, part="required"):
    """{tool: number of postings that ask for it}. part is 'required', 'nice' or 'any'.
    A posting counts once per tool."""
    # TODO: 'any' uses extract_tools; 'required' and 'nice' use extract_asks.
    raise NotImplementedError


def experience_buckets(postings):
    """Count postings by minimum years asked: '0-1', '2-3', '4-5', '6+', 'not stated'."""
    # TODO: all five keys must be present, even when a count is 0.
    raise NotImplementedError


def learn_next(counts, known, n=2):
    """The n most requested tools you do not know yet, ties broken by name."""
    # TODO
    raise NotImplementedError


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
