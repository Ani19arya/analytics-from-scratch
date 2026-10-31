"""Lesson 01: mean, median, spread and skew, by hand.

Rules: no `statistics`, `numpy`, `pandas` or `scipy` (the test checks this).
`csv` and `math` are fine. The built-in sorted() is fine.
Fill in every function marked TODO, then run: python3 test_lesson.py
"""
import csv
import math


def mean(values):
    """Return the arithmetic mean: sum of values divided by how many there are.
    Raise ValueError on an empty list."""
    # TODO
    raise NotImplementedError


def median(values):
    """Return the middle value of the sorted list.
    Odd count: the middle element. Even count: the average of the two middle elements.
    Raise ValueError on an empty list."""
    # TODO
    raise NotImplementedError


def std_dev(values):
    """Return the standard deviation of the whole list:
    sqrt( sum((x - mean)^2) / n ). Raise ValueError on an empty list."""
    # TODO
    raise NotImplementedError


def percentile(values, p):
    """Return the p-th percentile (p from 0 to 100) by linear interpolation:
    sort the values, rank = p / 100 * (n - 1), and if rank falls between two
    positions, go that fraction of the way from the lower value to the upper one.
    Raise ValueError on an empty list or a p outside 0 to 100."""
    # TODO
    raise NotImplementedError


def histogram(values, width):
    """Return a list of (bin_start, count) pairs. A value v belongs to the bin
    starting at floor(v / width) * width. List every bin from the lowest to the
    highest, including bins with a count of 0. Return [] for an empty list."""
    # TODO
    raise NotImplementedError


def skew_label(values, tolerance=0.01):
    """Return "right" if mean > median by more than tolerance * median,
    "left" if mean < median by more than that, otherwise "symmetric"."""
    # TODO
    raise NotImplementedError


def read_pay(path):
    """Read the pay_mid column of the CSV at path as a list of floats."""
    # TODO
    raise NotImplementedError


def summarise(path):
    """Return a dict with keys n, mean, median, gap (mean minus median),
    sd, p25, p75 and skew."""
    # TODO
    raise NotImplementedError
