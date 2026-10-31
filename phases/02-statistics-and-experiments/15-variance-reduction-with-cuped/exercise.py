"""Lesson 15: variance reduction with CUPED. Your turn.

Rules: no `statistics`, `numpy`, `pandas` or `scipy` (the test checks this).
`csv` and `math` are fine.
The README gives the formulas. Fill in every function, then run:
    python3 test_lesson.py
"""
import csv
import math

COVARIATES = ("pre_spend", "test_sessions")


def read_users(path):
    """One dict per user, in file order: variant (str), pre_spend (float, or
    None when blank), spend (float), test_sessions (int)."""
    # TODO
    raise NotImplementedError


def fill_missing(xs):
    """Replace each None with the mean of the values that are present.
    ValueError if every value is None."""
    # TODO
    raise NotImplementedError


def theta(xs, ys):
    """The CUPED coefficient. ValueError if the lists differ in length, have
    fewer than 2 items, or x does not vary."""
    # TODO
    raise NotImplementedError


def cuped_adjust(xs, ys, t):
    """The adjusted metric for every user, in order."""
    # TODO
    raise NotImplementedError


def diff_in_means(control, treatment):
    """Treatment mean minus control mean with the unpooled standard error
    (sample variances, n - 1). Return {"diff", "se", "p_value", "ci"}:
    two-sided p (1.0 when se is 0) and ci = diff +/- 1.959963984540054 * se.
    ValueError if a group has fewer than 2 values."""
    # TODO
    raise NotImplementedError


def summarise(path, covariate="pre_spend"):
    """Shelf minus control on spend, raw and CUPED-adjusted. covariate is one
    of COVARIATES (ValueError otherwise); fill its missing values first, and
    estimate theta once from all users in both groups. Return a dict:
    n                   {"control": users, "shelf": users}
    missing_covariate   users with no value for the covariate
    theta
    raw, cuped          diff_in_means(control, shelf) on spend / adjusted spend
    variance_reduction  1 - (cuped se / raw se) ** 2
    users_needed_share  (cuped se / raw se) ** 2"""
    # TODO
    raise NotImplementedError
