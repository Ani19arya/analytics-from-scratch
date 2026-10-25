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


def decompose(prior, current):
    """Split the revenue change into the part from each factor with the log method:
    effect_f = total_change * ln(current_f / prior_f) / ln(current_rev / prior_rev)
    Return a dict with keys visitors, conversion, aov, total, where
    total = current revenue - prior revenue. If revenue did not change, every effect is 0.0."""
    # TODO
    raise NotImplementedError


def main_driver(effects):
    """Return the factor name (visitors, conversion or aov) with the largest absolute effect."""
    # TODO
    raise NotImplementedError
