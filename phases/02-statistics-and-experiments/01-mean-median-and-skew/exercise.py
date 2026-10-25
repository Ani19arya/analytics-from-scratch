"""Lesson 01: mean, median and skew, by hand.

Rules: no `statistics` module, no sorting helpers beyond the built-in sorted().
Fill in every function marked TODO, then run: python3 test_lesson.py
"""
import csv


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
    """Return a dict with keys n, mean, median, gap (mean minus median) and skew."""
    # TODO
    raise NotImplementedError
