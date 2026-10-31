"""Lesson 10: correlation by hand, and Simpson's paradox. Your turn.

Rules: no `statistics`, `numpy`, `pandas` or `scipy` (the test checks this).
`csv` and `math` are fine.
Fill in every function marked TODO, then run: python3 test_lesson.py
"""
import csv
import math


def read_users(path):
    """Return a list of {"tenure": str, "notifications": int, "workouts": int},
    one per user, in file order. A blank workouts_28d means the user turned
    tracking off: the count is unknown, not 0, so skip that user."""
    # TODO
    raise NotImplementedError


def pearson_r(xs, ys):
    """Pearson correlation of two equal-length lists, written out by hand.
    Raise ValueError if the lengths differ, there are fewer than 2 pairs, or
    either variable does not vary at all (r is undefined then)."""
    # TODO
    raise NotImplementedError


def r_by_group(users):
    """Return {tenure: {"n": number of users, "r": r of notifications vs workouts}}
    for every tenure in the data. Use r = None for a group where r is undefined."""
    # TODO
    raise NotImplementedError


def within_group_r(users):
    """One correlation that ignores the differences BETWEEN tenure groups:
    subtract each group's own mean notifications and mean workouts from its
    users' values, then correlate the leftovers."""
    # TODO
    raise NotImplementedError


def is_simpson(overall_r, group_rs):
    """True if the overall r points one way and every group r (ignore None)
    points the other way. A 0 has no direction. False if no group r is left."""
    # TODO
    raise NotImplementedError


def summarise(path):
    """Return {"n", "overall_r", "by_tenure", "within_r", "simpson"} for the users
    file. Round every r to 4 decimals (keep None as None); by_tenure has the
    shape r_by_group returns."""
    # TODO
    raise NotImplementedError
