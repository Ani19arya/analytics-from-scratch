"""Lesson 12: percentile bootstrap intervals for a median and a ratio of sums.
Your turn.

Rules: no `statistics`, `numpy`, `pandas` or `scipy` (the test checks this).
`csv` and `random` are fine.
Fill in every function marked TODO, then run: python3 test_lesson.py
"""
import csv
import random


def read_orders(path):
    """Order values as floats, in file order. A blank order_value is not
    confirmed yet: skip it."""
    # TODO
    raise NotImplementedError


def read_sessions(path):
    """Return (per_session, per_user).
    per_session: one (1, revenue) pair per session, in file order.
    per_user:    one (number of sessions, total revenue) pair per user,
                 sorted by user_id as a number.
    Both shapes work with ratio_of_sums below."""
    # TODO
    raise NotImplementedError


def median(values):
    """The middle value; the average of the two middle values for an even count.
    Raise ValueError for an empty list."""
    # TODO
    raise NotImplementedError


def ratio_of_sums(pairs):
    """sum of second items / sum of first items (total revenue / total sessions).
    Raise ValueError if the first items add up to 0."""
    # TODO
    raise NotImplementedError


def bootstrap(units, statistic, n_boot=2000, seed=0):
    """Return a list of n_boot values of statistic(resample).
    Make ONE random.Random(seed), and build each resample with
    rng.choices(units, k=len(units)), so a seed always gives the same answer.
    Raise ValueError for no units or n_boot < 1."""
    # TODO
    raise NotImplementedError


def percentile(values, q):
    """The q-th quantile, 0 <= q <= 1: sort, go to position q * (n - 1), and
    interpolate linearly between the two neighbouring values.
    Raise ValueError for an empty list or q outside [0, 1]."""
    # TODO
    raise NotImplementedError


def percentile_interval(stats, level=0.95):
    """(low, high): the (1 - level) / 2 and 1 - (1 - level) / 2 percentiles."""
    # TODO
    raise NotImplementedError


def summarise(orders_path, sessions_path, n_boot=2000, seed=0):
    """Return a dict, money rounded to 2 decimals, intervals as (low, high) tuples:
    n_orders, median, median_ci              bootstrap the orders
    n_users, n_sessions, revenue_per_session
    ratio_ci_users                           bootstrap per_user (the right unit)
    ratio_ci_sessions                        bootstrap per_session (the wrong unit,
                                             for comparison)
    Use the same n_boot and seed for all three bootstraps."""
    # TODO
    raise NotImplementedError
