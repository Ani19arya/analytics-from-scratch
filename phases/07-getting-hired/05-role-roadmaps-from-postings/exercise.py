"""Exercise: data, business, product or BI analyst: which skills differ?

Fill in the functions marked TODO. Then run: python3 test_lesson.py
"""
import csv
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
DROP = os.path.join(HERE, "..", "..", "..", "data", "job-market", "2026-10", "by_country_skill.csv")
SKILLS = ["SQL", "Python", "Excel", "Tableau", "Power BI", "Looker", "R", "dbt"]
MIN_N = 30
FAMILIES = ["data", "business", "bi", "product"]

# TODO: one (family, compiled regex) per family, checked in order; the first match wins.
# bi: "business intelligence" or the word "bi". product: the word "product" (not "production").
# business: the word "business". data: the word "data" or "analytics". Ignore case.
# Think about which family must be checked before "business".
FAMILY_RULES = []


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_postings():
    return load_csv(os.path.join(DATA, "postings.csv"))


def load_drop(path=DROP):
    """The data drop's skill counts in the same shape as count_by_group: {country: {"n", "skills"}}."""
    counts = {}
    for r in load_csv(path):
        g = counts.setdefault(r["country"], {"n": int(r["postings_listing_any_tool"]), "skills": {s: 0 for s in SKILLS}})
        g["skills"][r["skill"]] = int(r["postings_listing_skill"])
    return counts


def title_family(title):
    """Return the family of the first rule in FAMILY_RULES that matches, or "other"."""
    # TODO
    raise NotImplementedError


def parse_tools(cell):
    """Return (set of SKILLS listed, True if the posting lists any tool at all).

    Split on commas, strip spaces, drop empty items. An item counts as a skill when it equals
    the skill name ignoring case ("power bi" is Power BI, "RStudio" is not R). Return the
    canonical names from SKILLS.
    """
    # TODO
    raise NotImplementedError


def count_by_group(postings, group_of):
    """Return {group: {"n": int, "skills": {skill: int for every skill in SKILLS}}}.

    group_of(posting) gives the group. Skip postings that list no tool at all. For the rest,
    add 1 to n and 1 to each skill the posting lists (once per posting, even if listed twice).
    """
    # TODO
    raise NotImplementedError


def share(counts, group, skill):
    """Percent of the group's n that list the skill. None if the group is missing or n is 0."""
    # TODO
    raise NotImplementedError


def pool(counts, groups):
    """Add the n and every skill count of the named groups into one {"n", "skills"}.
    Skip names that are not in counts."""
    # TODO
    raise NotImplementedError


def gaps(counts, a, b, min_n=MIN_N):
    """Return [(skill, share in a, share in b, share a - share b)] for every skill in SKILLS,
    sorted by the size of the difference, biggest first, ties by skill name.
    Return None if a or b is missing or has n below min_n."""
    # TODO
    raise NotImplementedError


def roadmap(counts, family, others, min_n=MIN_N, core_at=50.0, top=2):
    """Return {"core": [...], "stands_out": [...]} or None.

    rest = pool(counts, every name in others except family).
    None if the family is missing, or the family or rest has n below min_n.
    core: skills with a share >= core_at in the family, highest share first, ties by name.
    stands_out: up to `top` skills whose family share minus rest share is above 0,
    biggest difference first, ties by name.
    """
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    counts = count_by_group(load_postings(), lambda p: title_family(p["title"]))
    for fam in FAMILIES:
        print(fam, counts[fam]["n"], roadmap(counts, fam, FAMILIES))
    print(gaps(load_drop(), "US", "IN")[:3])
