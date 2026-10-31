"""Lesson 04: sample size for a two-proportion test, from the formula.

Rules: no scipy, no numpy, no `statistics` module (the test checks this). Use `math`.
Fill in every function marked TODO, then run: python3 test_lesson.py
"""
import csv
import math


def normal_cdf(z):
    """Given: P(Z <= z) for a standard normal (you wrote this in lesson 03)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def z_quantile(p):
    """Return z such that normal_cdf(z) == p, for 0 < p < 1.
    Use bisection: start with low = -10, high = 10, and halve the interval
    at least 100 times."""
    # TODO
    raise NotImplementedError


def sample_size_per_group(p1, p2, alpha=0.05, power=0.80):
    """Users needed in EACH group to detect p1 -> p2 with a two-sided test.

    z_a = z_quantile(1 - alpha / 2), z_b = z_quantile(power), p_bar = (p1 + p2) / 2
    n = (z_a * sqrt(2 * p_bar * (1 - p_bar)) + z_b * sqrt(p1 * (1 - p1) + p2 * (1 - p2)))^2
        / (p2 - p1)^2
    Round UP to a whole user. Raise ValueError if p1 == p2."""
    # TODO
    raise NotImplementedError


def sample_size_for_lift(baseline, relative_lift, alpha=0.05, power=0.80):
    """Same as above with p2 = baseline * (1 + relative_lift).
    relative_lift = 0.10 means a 10% relative improvement (10% -> 11%),
    NOT 10 percentage points (10% -> 20%). Raise ValueError if relative_lift is 0."""
    # TODO
    raise NotImplementedError


def weeks_needed(n_per_group, weekly_visitors, groups=2, min_weeks=1):
    """Whole weeks needed to fill every group: ceil(n * groups / weekly), but never
    fewer than min_weeks, so the test always covers full weekly cycles.
    Raise ValueError if weekly_visitors is not positive."""
    # TODO
    raise NotImplementedError


def plan(path, relative_lift, alpha=0.05, power=0.80, min_weeks=2):
    """For each row in the pages CSV return a dict with keys
    page, baseline_rate, weekly_visitors, n_per_group and weeks
    (weeks uses weeks_needed with min_weeks). Keep the file order."""
    # TODO
    raise NotImplementedError
