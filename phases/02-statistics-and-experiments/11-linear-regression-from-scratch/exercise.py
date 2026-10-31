"""Lesson 11: simple linear regression from the formulas. Your turn.

Rules: no `statistics`, `numpy`, `pandas`, `scipy` or `statsmodels` (the test
checks this). `csv` and `math` are fine.
Fill in every function marked TODO, then run: python3 test_lesson.py
"""
import csv
import math


def read_members(path):
    """Return (visits, spend): two lists in file order, visits as int and spend
    as float. A blank spend_30d failed to sync: it is unknown, so skip the member."""
    # TODO
    raise NotImplementedError


def fit_line(xs, ys):
    """Least squares line through the points. Return {"slope", "intercept"}.
    Raise ValueError if the lists differ in length, have fewer than 2 points,
    or x does not vary."""
    # TODO
    raise NotImplementedError


def predict(fit, x):
    """The line's value at x."""
    # TODO
    raise NotImplementedError


def r_squared(xs, ys, fit):
    """1 - (sum of squared residuals) / (sum of squared deviations of y from its mean).
    Raise ValueError if y does not vary."""
    # TODO
    raise NotImplementedError


def slope_se(xs, ys, fit):
    """Standard error of the slope. The residual variance divides by n - 2,
    because the line used up two numbers (slope and intercept).
    Raise ValueError for fewer than 3 points."""
    # TODO
    raise NotImplementedError


def slope_ci(slope, se, crit=1.96):
    """(low, high) = slope -/+ crit * se."""
    # TODO
    raise NotImplementedError


def summarise(path):
    """Return {"n", "slope", "intercept", "r_squared", "slope_se", "slope_ci",
    "residual_sd"} for the members file, every number rounded to 4 decimals.
    slope_ci is a (low, high) tuple; residual_sd is sqrt(SSE / (n - 2))."""
    # TODO
    raise NotImplementedError
