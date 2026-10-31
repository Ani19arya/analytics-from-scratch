"""Lesson 08: retention curves and churn. Your turn.

Rules: standard library only (csv, datetime).
Read "The idea" in the README for the definitions, fill in every TODO,
then run: python3 test_lesson.py
"""
import csv
import datetime


def load(users_path, visits_path):
    """Return (signups, offsets): {user_id: signup date} and
    {user_id: set of day offsets with a visit} for every signed-up user.
    Decide what to do with visits before signup and visits by unknown users."""
    # TODO
    raise NotImplementedError


def classic_retention(signups, offsets, n, as_of):
    """(retained, eligible) for classic day-n retention."""
    # TODO
    raise NotImplementedError


def unbounded_retention(signups, offsets, n, as_of):
    """(retained, eligible) for unbounded day-n retention."""
    # TODO
    raise NotImplementedError


def rate(pair):
    """retained / eligible, or None when nobody is eligible."""
    # TODO
    raise NotImplementedError


def week_start(day):
    """The Monday on or before a date, as 'YYYY-MM-DD' text."""
    # TODO
    raise NotImplementedError


def cohort_curves(signups, offsets, days, as_of, kind="classic"):
    """{signup week Monday: {n: rate or None}} for each n in days."""
    # TODO
    raise NotImplementedError
