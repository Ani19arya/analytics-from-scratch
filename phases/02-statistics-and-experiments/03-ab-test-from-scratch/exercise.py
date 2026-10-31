"""Lesson 03: a two-proportion z-test from the formula.

Rules: no scipy, no statsmodels, no numpy, no `statistics` module (the test
checks this). Use `math` and `csv`.
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


def srm_check(n_a, n_b, expected_share_a=0.5):
    """Sample ratio mismatch check. Return a dict with keys:
    chi2       sum over both groups of (observed - expected)^2 / expected,
               where expected_a = (n_a + n_b) * expected_share_a
    p_value    2 * (1 - normal_cdf(sqrt(chi2)))   (a chi-square with 1 degree
               of freedom is a z squared)
    Raise ValueError if n_a + n_b == 0."""
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
    If se is 0 (nobody converted, or everybody did), return z = 0.0 and p_value = 1.0.
    Raise ValueError if either group has no users."""
    # TODO
    raise NotImplementedError


def diff_ci(conv_a, n_a, conv_b, n_b, z=1.96):
    """Return (low, high), a confidence interval for the lift p_b - p_a:
    lift +/- z * sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b).
    This standard error is NOT pooled. Raise ValueError if either group has no users."""
    # TODO
    raise NotImplementedError


def decide(result, alpha=0.05, min_lift=0.0):
    """Return "ship" if result["p_value"] < alpha, result["lift"] > 0 and
    result["lift"] >= min_lift. Otherwise return "do not ship"."""
    # TODO
    raise NotImplementedError
