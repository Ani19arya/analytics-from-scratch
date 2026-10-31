"""Exercise: with 40 postings and 10 hours this week, which ones are worth an application?

Fill in the functions marked TODO. Then run: python3 test_lesson.py
"""
import csv
import datetime
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

STALE_DAYS = 30          # freshness falls from 1 to 0 over this many days
MUST_WEIGHT = 0.75       # fit = 0.75 x must-have share + 0.25 x nice-to-have share
REPOST_FACTOR = 0.5      # a reposted listing is worth half: its date is not the employer's
HARD_FLAGS = {"fee_to_apply", "unpaid_work", "seniority_mismatch"}

# TODO: patterns for the red flags. Read the notes column of data/postings.csv first.
FEE = None
UNPAID = None
SENIOR_WORDS = None


def load_postings():
    with open(os.path.join(DATA, "postings.csv"), newline="") as f:
        return list(csv.DictReader(f))


def load_profile():
    with open(os.path.join(DATA, "profile.json")) as f:
        return json.load(f)


def freshness(first_seen, as_of):
    """1.0 for a posting first seen on as_of, falling in a straight line to 0.0 at STALE_DAYS
    days old, and 0.0 after that. Blank or unreadable dates count as stale (0.0).
    A date after as_of counts as 1.0. Dates are ISO strings like 2026-10-31."""
    # TODO
    raise NotImplementedError


def fit(posting, skills):
    """Return (fit score from 0 to 1, sorted list of missing must-haves in lower case).

    must_have and nice_to_have are ";" separated lists. Compare without case.
    fit = MUST_WEIGHT x share of must-haves you have + (1 - MUST_WEIGHT) x share of
    nice-to-haves you have. An empty list counts as a share of 1.
    """
    # TODO
    raise NotImplementedError


def red_flags(posting, profile):
    """Return the sorted list of flag codes that apply:

    fee_to_apply        the notes ask the candidate to pay (and do not say "no", "never" or "not")
    unpaid_work         the notes ask for unpaid trial, test or pilot work (same negation rule)
    seniority_mismatch  labelled "Entry Level" but the title is senior (senior, sr, lead,
                        principal, staff, manager, head, director) or salary_min_usd is at
                        least profile["entry_salary_ceiling_usd"]
    repost              source is "repost"
    """
    # TODO
    raise NotImplementedError


def value(posting, profile):
    """0.0 if the posting has a hard flag or misses more than one must-have.
    Otherwise 100 x fit x (0.5 + 0.5 x freshness), multiplied by REPOST_FACTOR for a repost."""
    # TODO
    raise NotImplementedError


def choose(items, budget_hours):
    """items: [(id, value, hours)], hours in steps of 0.5.
    Return (sorted list of chosen ids, total value, total hours): the set with the MOST total
    value whose hours fit in budget_hours. Never choose an item with value 0 or less."""
    # TODO
    raise NotImplementedError


def plan(postings, profile):
    items = [(p["posting_id"], value(p, profile), float(p["est_hours"])) for p in postings]
    return choose(items, profile["weekly_hours"])


if __name__ == "__main__":
    ids, total, hours = plan(load_postings(), load_profile())
    print(ids, round(total, 1), hours)
