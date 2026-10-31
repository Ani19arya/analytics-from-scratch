"""Lesson 10: diagnose a metric drop. Your turn.

Rules: standard library only (csv).
The rules for each function are in "The idea" in the README. Fill in every TODO,
then run: python3 test_lesson.py
"""
import csv

DROP_THRESHOLD = -0.05   # a fall of more than 5% is worth diagnosing


def load(path):
    """Return the rows as dicts, with server_users and dau as ints."""
    # TODO
    raise NotImplementedError


def totals(rows, date, dims=()):
    """{key: [dau, server_users]} for one date; key is the tuple of the dims' values."""
    # TODO
    raise NotImplementedError


def pct_change(old, new):
    """(new - old) / old, or None when old is 0."""
    # TODO
    raise NotImplementedError


def contributions(rows, dim, base_date, date):
    """[(value, base_dau, dau, change, share_of_change), ...], biggest fall first, ties by value."""
    # TODO
    raise NotImplementedError


def coverage(rows, date, dims):
    """{key: dau / server_users}, None where there are no server users."""
    # TODO
    raise NotImplementedError


def diagnose(rows, base_date, date):
    """{"dau_change", "server_change", "verdict", "suspect"}.
    verdict is "no drop", "real" or "tracking"; suspect is a (platform, app_version) or None."""
    # TODO
    raise NotImplementedError


def corrected_dau(rows, date, suspect):
    """DAU on date if the suspect segment had the same coverage as every other segment."""
    # TODO
    raise NotImplementedError
