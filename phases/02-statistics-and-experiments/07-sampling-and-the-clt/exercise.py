"""Lesson 07: sampling and the central limit theorem. Your turn.

Rules: no `statistics`, `numpy`, `pandas` or `scipy` (the test checks this).
`csv`, `math` and `random` are fine. Use random.Random(seed), never the shared
module-level functions such as random.choices(), so a seed repeats exactly.
Fill in every function marked TODO, then run: python3 test_lesson.py
"""
import csv
import math
import random


def mean(values):
    """Sum divided by count. Raise ValueError on an empty list."""
    # TODO
    raise NotImplementedError


def population_sd(values):
    """SD of a COMPLETE population: sqrt(sum((x - mean)^2) / N).
    Use it only when the list is everything you care about."""
    # TODO
    raise NotImplementedError


def sample_sd(values):
    """SD ESTIMATED from a sample: sqrt(sum((x - mean)^2) / (n - 1)).
    Raise ValueError if there are fewer than 2 values."""
    # TODO
    raise NotImplementedError


def standard_error(values):
    """Estimated standard error of the mean of this sample: sample_sd(values) / sqrt(n)."""
    # TODO
    raise NotImplementedError


def sample_means(population, n, draws, seed):
    """Make rng = random.Random(seed) once. Then, `draws` times, take a random sample
    of n values with replacement (rng.choices(population, k=n)) and record its mean.
    Return the list of `draws` means. Raise ValueError if n < 1, draws < 0 or the
    population is empty."""
    # TODO
    raise NotImplementedError


def share_within(values, centre, half_width):
    """Share of values v with centre - half_width <= v <= centre + half_width.
    Raise ValueError on an empty list."""
    # TODO
    raise NotImplementedError


def read_orders(path):
    """The order_value column of a CSV as a list of floats."""
    # TODO
    raise NotImplementedError


def read_weeks(path):
    """{week_start: [order values]} from data/weeks.csv."""
    # TODO
    raise NotImplementedError


def summarise(population_path, weeks_path, n=18, draws=10000, seed=1):
    """Return a dict with these keys:
    pop_mean, pop_sd (population_sd), true_se (pop_sd / sqrt(n)),
    mean_of_means and sd_of_means (mean and sample_sd of sample_means(...)),
    share_within_1_96 (share of those means within 1.96 * true_se of pop_mean),
    week1_mean, week1_se, week2_mean, week2_se (earliest week first; the SEs use
    standard_error, because a real week is a sample), change (week 2 minus week 1)
    and change_se (sqrt(week1_se^2 + week2_se^2))."""
    # TODO
    raise NotImplementedError
