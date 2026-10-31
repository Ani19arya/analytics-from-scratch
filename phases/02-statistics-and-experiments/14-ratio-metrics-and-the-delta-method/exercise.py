"""Lesson 14: ratio metrics and the delta method. Your turn.

Rules: no `statistics`, `numpy`, `pandas` or `scipy` (the test checks this).
`csv` and `math` are fine.
The README gives the formulas. Fill in every function, then run:
    python3 test_lesson.py
"""
import csv
import math


def read_users(path):
    """{variant: [(applications, replies), ...]}: one pair of ints per user,
    in file order."""
    # TODO
    raise NotImplementedError


def ratio(pairs):
    """Total replies / total applications. ValueError if there are no applications."""
    # TODO
    raise NotImplementedError


def naive_var(pairs):
    """The variance you would get if every application were independent:
    R (1 - R) / total applications."""
    # TODO
    raise NotImplementedError


def delta_var(pairs):
    """Delta method variance of the ratio, with the user as the independent
    unit. Users with 0 applications count as users. ValueError for fewer than
    two users or no applications."""
    # TODO
    raise NotImplementedError


def compare(control, treatment, method="delta"):
    """Treatment ratio minus control ratio. method is "delta" or "naive"
    (ValueError otherwise). Return a dict:
    control, treatment   the two ratios
    diff                 treatment - control
    se                   standard error of diff
    z, p_value           two-sided; z = 0 and p = 1 when se is 0
    ci                   (low, high), diff +/- 1.959963984540054 * se"""
    # TODO
    raise NotImplementedError


def summarise(path):
    """Return a dict:
    users          {"control": n, "quick_apply": n}
    applications   {"control": total, "quick_apply": total}
    naive, delta   compare(control, quick_apply, method)
    design_effect  (delta se / naive se) squared"""
    # TODO
    raise NotImplementedError
