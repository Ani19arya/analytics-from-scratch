"""Lesson 08: a permutation test, written from scratch. Your turn.

Rules: no `statistics`, `numpy`, `pandas` or `scipy` (the test checks this).
`csv`, `itertools`, `math` and `random` are fine. Use random.Random(seed), never
the shared module-level functions, so a seed repeats exactly.
Fill in every function marked TODO, then run: python3 test_lesson.py
"""
import csv
import itertools
import math
import random

ALTERNATIVES = ("two-sided", "greater", "less")


def read_groups(path):
    """Return {"control": [floats], "side_dish": [floats]} in file order.
    A blank order_value is a logging failure, not a 0 dollar order: skip it."""
    # TODO
    raise NotImplementedError


def mean_diff(a, b):
    """mean(b) - mean(a). Raise ValueError if either list is empty."""
    # TODO
    raise NotImplementedError


def permutation_test(a, b, n_perm=10000, seed=0, alternative="two-sided"):
    """Shuffle the labels n_perm times and count how often the shuffled
    mean_diff is at least as extreme as the observed one.

    alternative: "two-sided" (|diff| >= |observed|), "greater" (diff >= observed)
    or "less" (diff <= observed). Compare with a tolerance of 1e-9, because two
    splits with the same difference can differ in the last digit of a float.
    Return {"observed", "extreme", "n_perm", "p_value"} where
    p_value = (extreme + 1) / (n_perm + 1).
    Do not change the caller's lists. Raise ValueError for an empty group,
    n_perm < 1 or an unknown alternative."""
    # TODO
    raise NotImplementedError


def exact_test(a, b, alternative="two-sided", max_splits=200000):
    """List EVERY way to choose len(a) of the pooled values as the control group
    (itertools.combinations over positions, so repeated values still count
    separately). Return {"observed", "extreme", "splits", "p_value"} with
    p_value = extreme / splits (the observed split is in the list, so no +1).
    Raise ValueError if math.comb(len(a) + len(b), len(a)) > max_splits, and for
    the same bad inputs as permutation_test."""
    # TODO
    raise NotImplementedError


def summarise(orders_path, pilot_path, n_perm=10000, seed=0):
    """Return a dict with these keys, numbers rounded to 4 decimals:
    n_control, n_side_dish           values read from the orders file
    observed, p_two_sided            permutation test on the orders file
    pilot_observed, pilot_exact_p    exact test on the pilot file (two-sided)
    pilot_splits                     how many splits the exact test listed
    pilot_permutation_p              permutation test on the pilot file (two-sided)"""
    # TODO
    raise NotImplementedError
