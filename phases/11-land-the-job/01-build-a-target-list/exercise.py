"""Exercise: where are the analyst roles you can get, and which 30 companies go on your list?

Part 1 reads the REAL data drop (data/job-market/2026-10, 25 October 2026) to choose countries.
Part 2 scores the companies in a SYNTHETIC set of saved postings to build a target list.

Fill in every function marked TODO. Then run: python3 test_lesson.py
"""
import csv
import datetime
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LESSON = os.path.dirname(HERE) if os.path.basename(HERE) == "solution" else HERE
DATA = os.path.join(LESSON, "data")
DROP_DIR = os.path.join(LESSON, "..", "..", "..", "data", "job-market", "2026-10")
MIN_POSTINGS = 30
NOT_A_COUNTRY = {"UNKNOWN"}
AS_OF = "2026-10-31"

PROFILE = {
    "countries": ["GB", "IE"],
    "levels": ["Entry Level", "Mid Level", "Not Specified"],
    "skills": ["SQL", "Excel", "Power BI", "Python"],
    "min_fit": 0.5,
    "max_age": 30,
    "as_of": AS_OF,
}


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_postings():
    return load_csv(os.path.join(DATA, "postings.csv"))


def load_drop(folder=DROP_DIR):
    """The three drop files as {country: {"postings", "companies", "levels": {label: n},
    "skills": {skill: n}, "any_tool": n}}."""
    drop = {}
    for r in load_csv(os.path.join(folder, "by_country.csv")):
        drop[r["country"]] = {"postings": int(r["postings"]), "companies": int(r["companies"]),
                              "levels": {}, "skills": {}, "any_tool": 0}
    for r in load_csv(os.path.join(folder, "by_country_seniority.csv")):
        drop[r["country"]]["levels"][r["experience"]] = int(r["postings"])
    for r in load_csv(os.path.join(folder, "by_country_skill.csv")):
        drop[r["country"]]["skills"][r["skill"]] = int(r["postings_listing_skill"])
        drop[r["country"]]["any_tool"] = int(r["postings_listing_any_tool"])
    return drop


# ---------- Part 1: countries, from the real drop ----------

def where_to_look(drop, levels, min_postings=MIN_POSTINGS):
    """Return one dict per country with keys country, postings, companies, at_level,
    share_of_labelled.

    Leave out countries in NOT_A_COUNTRY and countries with fewer than min_postings postings.
    at_level: postings whose experience label is in levels (Not Specified counts if it is in levels).
    share_of_labelled: of the postings that HAVE a label (not Not Specified), the percent whose
    label is in levels. None when no posting has a label.
    Sort by at_level, biggest first, ties by country code.
    """
    # TODO
    raise NotImplementedError


def skill_share(drop, country, skill):
    """Percent of the country's postings that list any tool which list this skill.
    None if the country is missing or no posting lists a tool."""
    # TODO
    raise NotImplementedError


# ---------- Part 2: companies, from saved postings ----------

def parse_skills(cell):
    """Return the set of skills in a comma separated cell: lower-case, stripped, no empty items."""
    # TODO
    raise NotImplementedError


def skill_fit(posting_skills, my_skills):
    """Share (0 to 1) of the posting's skills that are in my_skills, ignoring case.
    None when the posting lists no skills."""
    # TODO
    raise NotImplementedError


def age_days(posted_date, as_of):
    """Whole days from posted_date to as_of, both "YYYY-MM-DD"."""
    # TODO
    raise NotImplementedError


def dedupe(postings):
    """One row per role. A role is (company, title ignoring case and extra spaces, country).
    Keep the row with the earliest posted_date: that is when the role was first seen."""
    # TODO
    raise NotImplementedError


def is_match(p, profile):
    """True when the country and seniority are in the profile, the age is between 0 and
    max_age days (both included), and the skill fit is None or at least min_fit."""
    # TODO
    raise NotImplementedError


def score_companies(postings, profile):
    """Dedupe, keep matching roles, group by company, and return one dict per company:
    company, roles, mean_fit (an unknown fit counts as 0.5), newest_age (age of the newest
    matching role), score.

    score = 40 * mean_fit + 30 * max(0, 1 - newest_age / 30) + 30 * min(roles, 5) / 5
    Sort by score (round it to 6 places for the sort), highest first; ties by more roles,
    then the smaller newest_age, then company name.
    """
    # TODO
    raise NotImplementedError


def target_list(postings, profile, n=30):
    """The first n companies from score_companies."""
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    drop = load_drop()
    for r in where_to_look(drop, ["Entry Level", "Mid Level"])[:5]:
        print(r)
    for r in target_list(load_postings(), PROFILE)[:5]:
        print(r)
