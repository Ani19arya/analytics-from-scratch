"""Lesson 03: a two-proportion z-test from the formula.

Rules: no scipy, no statsmodels, no `statistics` module. Use `math`.
Fill in every function marked TODO, then run: python3 test_lesson.py
"""
import csv
import math


def normal_cdf(z):
    """P(Z <= z) for a standard normal: 0.5 * (1 + erf(z / sqrt(2)))."""
    # TODO
    raise NotImplementedError


def count_conversions(path):
    """Read the experiment CSV and return {"A": (conversions, users), "B": (conversions, users)}."""
    # TODO
    raise NotImplementedError


def two_proportion_ztest(conv_a, n_a, conv_b, n_b):
    """Return a dict with keys:
    p_a, p_b        the two conversion rates
    lift            p_b - p_a (absolute difference)
    p_pool          (conv_a + conv_b) / (n_a + n_b)
    se              sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
    z               lift / se
    p_value         two-sided: 2 * (1 - normal_cdf(abs(z)))
    """
    # TODO
    raise NotImplementedError


def decide(result, alpha=0.05):
    """Return "ship" if result["p_value"] < alpha and result["lift"] > 0,
    otherwise "do not ship"."""
    # TODO
    raise NotImplementedError
