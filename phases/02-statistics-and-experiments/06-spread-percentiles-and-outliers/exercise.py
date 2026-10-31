"""Lesson 06: outliers, box plots and robust summaries. Your turn.

Rules: no `statistics`, `numpy`, `pandas` or `scipy` (the test checks this).
`csv` and `math` are fine. The built-in sorted() is fine.
Fill in every function marked TODO, then run: python3 test_lesson.py
"""
import csv
import math


def percentile(values, p):
    """The p-th percentile (p from 0 to 100) by the INCLUSIVE method: sort the values,
    rank = p / 100 * (n - 1), and if rank falls between two positions go that fraction
    of the way from the lower value to the upper one. This matches Excel PERCENTILE.INC
    and statistics.quantiles(..., method="inclusive").
    Raise ValueError on an empty list or a p outside 0 to 100."""
    # TODO
    raise NotImplementedError


def median(values):
    """The 50th percentile."""
    # TODO
    raise NotImplementedError


def quartiles(values):
    """Return (Q1, median, Q3): the 25th, 50th and 75th percentiles."""
    # TODO
    raise NotImplementedError


def iqr_fences(values, k=1.5):
    """Return (low, high) = (Q1 - k * IQR, Q3 + k * IQR), where IQR = Q3 - Q1."""
    # TODO
    raise NotImplementedError


def flag_outliers(values, k=1.5):
    """The values strictly below the low fence or strictly above the high fence, sorted.
    A value exactly on a fence is NOT an outlier."""
    # TODO
    raise NotImplementedError


def mad(values):
    """Median absolute deviation: the median of abs(v - median(values))."""
    # TODO
    raise NotImplementedError


def mean(values):
    """Sum divided by count. Raise ValueError on an empty list."""
    # TODO
    raise NotImplementedError


def sample_sd(values):
    """sqrt(sum((v - mean)^2) / (n - 1)). Raise ValueError with fewer than 2 values."""
    # TODO
    raise NotImplementedError


def box_plot_stats(values, k=1.5):
    """Return a dict with q1, median, q3, iqr, low_fence, high_fence,
    low_whisker and high_whisker (the smallest and largest values that are inside
    the fences, fences included) and outliers (as flag_outliers returns them)."""
    # TODO
    raise NotImplementedError


def read_rows(path):
    """Read the CSV as a list of dicts with response_id and years_experience as int
    and base_pay as float."""
    # TODO
    raise NotImplementedError


def entry_errors(rows, floor=1000):
    """The sorted response_ids of rows whose base_pay is below floor. Nobody earns
    under 1,000 dollars a year in a full-time analyst job: these were typed in thousands."""
    # TODO
    raise NotImplementedError


def describe(values):
    """Return a dict with n, mean, sd (sample_sd), median, iqr and mad."""
    # TODO
    raise NotImplementedError


def summarise(path):
    """Return a dict with:
    errors:  entry_errors(rows), the list of response_ids
    flagged: how many rows flag_outliers finds in all the pay values
    box:     box_plot_stats of all the pay values
    all:     describe(all pay values)
    cleaned: describe(pay without the entry errors)       <- the honest version
    trimmed: describe(pay without every flagged outlier)  <- the trap, for comparison"""
    # TODO
    raise NotImplementedError
