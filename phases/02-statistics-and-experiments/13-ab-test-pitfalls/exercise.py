"""Lesson 13: A/B test pitfalls. Your turn.

Rules: no `statistics`, `numpy`, `pandas` or `scipy` (the test checks this).
`csv`, `math` and `random` are fine.
The README gives the formulas. Fill in every function, then run:
    python3 test_lesson.py
"""
import csv
import math
import random

METRICS = ("signups", "saves", "shares")


def read_daily(path):
    """One dict per row of data/daily.csv, every count as an int."""
    # TODO
    raise NotImplementedError


def totals(rows, last_day=None):
    """{variant: {"users", "signups", "saves", "shares"}} summed over days
    1..last_day (all days when last_day is None)."""
    # TODO
    raise NotImplementedError


def two_proportion_p(c_a, n_a, c_b, n_b):
    """Two-sided p-value of the pooled two-proportion z-test (lesson 03).
    p = 1.0 when the pooled rate is 0 or 1. ValueError if a group has no users."""
    # TODO
    raise NotImplementedError


def chi2_sf(x, df):
    """P(chi-square with df degrees of freedom > x) for a whole number df >= 1.
    ValueError for any other df. 1.0 for x <= 0."""
    # TODO
    raise NotImplementedError


def srm_check(counts, weights=None):
    """Sample ratio check. counts: {group: users}; weights: {group: planned
    share}, equal shares when None. Return {"chi2", "df", "p_value"}.
    ValueError for fewer than two groups or no users."""
    # TODO
    raise NotImplementedError


def srm_culprits(counts, threshold=0.001):
    """Sorted list of the groups whose own size, tested against all the other
    groups together (two groups, planned shares 1/k and 1 - 1/k), has a
    p-value below threshold."""
    # TODO
    raise NotImplementedError


def bonferroni(pvalues):
    """Adjusted p-values, input order, capped at 1."""
    # TODO
    raise NotImplementedError


def holm(pvalues):
    """Holm step-down adjusted p-values, input order, capped at 1."""
    # TODO
    raise NotImplementedError


def benjamini_hochberg(pvalues):
    """Benjamini-Hochberg adjusted p-values, input order, capped at 1."""
    # TODO
    raise NotImplementedError


def peeking_curve(rows, control, variant, metric):
    """[(day, p-value)] for every day, using all users up to and including that day."""
    # TODO
    raise NotImplementedError


def simulate_peeking(n_sims, n_days, users_per_day, rate, alpha=0.05, seed=0):
    """Simulate n_sims A/A tests with one random.Random(seed). Each day each of
    the two groups gets users_per_day users who convert with probability rate.
    Return (share of tests with p < alpha on ANY day, share with p < alpha on
    the LAST day). ValueError if n_sims, n_days or users_per_day is below 1."""
    # TODO
    raise NotImplementedError


def analyse(path, control="A", alpha=0.05):
    """Return a dict:
    users    {variant: users}
    srm_p    p-value of the sample ratio check on all groups (equal shares)
    dropped  srm_culprits(...) if srm_p < 0.001, else []
    tests    one dict per kept challenger and metric, sorted by variant, then
             METRICS order: variant, metric, lift (challenger rate minus control
             rate, rounded to 5 decimals), p, holm, bh
    wins_raw, wins_holm, wins_bh
             "B:signups"-style names, in tests order, where lift > 0 and the
             raw / Holm / BH p-value is below alpha
    The Holm and BH family is every test in `tests`."""
    # TODO
    raise NotImplementedError
