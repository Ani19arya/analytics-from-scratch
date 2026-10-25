"""Exercise: read job postings like data, with regex and counting.

load_postings, role_text and main are done for you. Fill in everything marked TODO.
Then run: python3 test_lesson.py
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

# TODO: match "3+ years", "2-4 years", "0 to 2 years" and "At least 3 years".
# Group 1 is the low number, group 2 the high number (absent for open ended).
YEARS = None

# TODO: VISA_NO matches refusals ("unable to sponsor", "will not sponsor",
# "without visa sponsorship"). VISA_YES matches any other mention of sponsoring.
VISA_NO = None
VISA_YES = None


def load_postings(data_dir=DATA):
    with open(os.path.join(data_dir, "postings.csv"), newline="") as f:
        return list(csv.DictReader(f))


def role_text(text):
    """Drop the company boilerplate: keep everything from 'About the role:' on."""
    i = text.find("About the role:")
    return text if i < 0 else text[i:]


def extract_tools(text):
    """Sorted list of tool names the role text asks for."""
    # TODO: search role_text(text) with each pattern in TOOL_PATTERNS.
    raise NotImplementedError


def extract_years(text):
    """(min_years, max_years) from the first experience phrase, max None if open ended. None if absent."""
    # TODO: search role_text(text) with YEARS, return ints.
    raise NotImplementedError


def visa_status(text):
    """'no' if it refuses sponsorship, 'yes' if it mentions sponsoring, else 'silent'."""
    # TODO: check VISA_NO before VISA_YES. "will not sponsor" contains "sponsor".
    raise NotImplementedError


def skill_counts(postings):
    """{tool: number of postings that name it}. A posting counts once per tool."""
    # TODO
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
    counts = skill_counts(postings)
    total = len(postings)
    print("postings:", total)
    for t, c in sorted(counts.items(), key=lambda x: -x[1]):
        print("%-9s %4d  %5.1f%%" % (t, c, 100.0 * c / total))
    print(experience_buckets(postings))
    print("learn next if you know SQL and Excel:", learn_next(counts, {"SQL", "Excel"}))


if __name__ == "__main__":
    main()
