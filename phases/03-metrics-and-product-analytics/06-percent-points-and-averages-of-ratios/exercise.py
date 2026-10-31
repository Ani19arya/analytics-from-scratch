"""Lesson 06: percent vs points, ratio of sums vs average of ratios. Your turn.

Rules: standard library only (csv).
Rates are fractions in this file: 0.0237 means 2.37%.
Fill in every function marked TODO, then run: python3 test_lesson.py
"""
import csv


def read_days(path):
    """A list of dicts: date as text, visits and orders as int."""
    # TODO
    raise NotImplementedError


def ratio_of_sums(rows):
    """Total orders divided by total visits. None when total visits is 0."""
    # TODO
    raise NotImplementedError


def average_of_ratios(rows):
    """The plain average of each day's orders / visits. A day with 0 visits has no
    rate: skip it (do not count it as 0). None when no day has visits."""
    # TODO
    raise NotImplementedError


def weighted_average_of_ratios(rows):
    """Each day's rate weighted by that day's visits:
    sum(rate * visits) / sum(visits), over days with visits. None when there are none.
    (Work out on paper why this always equals ratio_of_sums.)"""
    # TODO
    raise NotImplementedError


def by_month(rows):
    """{'YYYY-MM': [the rows of that month]}, from the first 7 characters of date."""
    # TODO
    raise NotImplementedError


def point_change(old, new):
    """The change between two rates in percentage points: (new - old) * 100.
    2% to 2.5% is +0.5 points."""
    # TODO
    raise NotImplementedError


def percent_change(old, new):
    """The relative change in percent: (new - old) / old * 100. 2% to 2.5% is +25%.
    None when old is 0."""
    # TODO
    raise NotImplementedError


def describe_change(old, new):
    """One line that says both, in exactly this format:
    "%.2f%% to %.2f%%: %+.2f points (%+.1f%%)" % (old * 100, new * 100, points, percent)
    for example "2.00% to 2.50%: +0.50 points (+25.0%)".
    When percent_change is None, put "n/a" inside the brackets instead."""
    # TODO
    raise NotImplementedError


def summarise(path):
    """Return a dict with one entry per month (the two months in the file, e.g. '2026-09'),
    each a dict with visits, orders, ratio_of_sums and average_of_ratios; plus
    change_ratio_of_sums and change_average_of_ratios: describe_change from the
    earlier month to the later one, for each method."""
    # TODO
    raise NotImplementedError
