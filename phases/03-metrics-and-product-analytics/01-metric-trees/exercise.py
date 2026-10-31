"""Lesson 01: metric trees. Your turn.

revenue = visitors x conversion x average order value (AOV)
Rules: standard library only (csv, math).
Fill in every function marked TODO, then run: python3 test_lesson.py
"""
import csv
import math

FACTORS = ("visitors", "conversion", "aov")


def build_tree(visitors, orders, revenue):
    """Return the tree for one period as a dict with keys
    visitors, orders, revenue, conversion (orders / visitors), aov (revenue / orders).
    Use 0.0 for a ratio whose denominator is 0."""
    # TODO
    raise NotImplementedError


def load_weeks(path, split_date, channel=None):
    """Sum visitors, orders and revenue for the days before split_date (prior)
    and on or after it (current). Dates are 'YYYY-MM-DD' text, so string
    comparison works. If channel is given, use only that channel's rows.
    Return (prior_tree, current_tree), each built with build_tree."""
    # TODO
    raise NotImplementedError


def log_mean(a, b):
    """The logarithmic mean of two positive numbers:
    L(a, b) = (a - b) / (ln a - ln b), and L(a, a) = a."""
    # TODO
    raise NotImplementedError


def decompose(prior, current):
    """Split the revenue change into the part from each factor (LMDI):
    effect_f = log_mean(current revenue, prior revenue) * ln(current_f / prior_f)
    Return a dict with keys visitors, conversion, aov, total, where
    total = current revenue - prior revenue. The three effects add up to total,
    even when revenue did not change.
    If revenue or any factor is 0 in either period, set the three factor
    effects to None (a log of 0 is undefined) and still fill in total."""
    # TODO
    raise NotImplementedError


def main_driver(effects):
    """Return the factor name (visitors, conversion or aov) with the largest absolute effect.
    A tie goes to the factor listed first in FACTORS. Return None if the effects are None."""
    # TODO
    raise NotImplementedError
