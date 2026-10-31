"""Lesson 02: confidence intervals by hand.

Rules: no `statistics`, `numpy`, `scipy` or `pandas` (the test checks this).
`math` is fine for sqrt.
Fill in every function marked TODO, then run: python3 test_lesson.py
"""
import csv
import math

# Two-sided critical values of the standard normal distribution: the middle
# 90%, 95% or 99% of the bell curve lies between -Z and +Z.
Z = {0.90: 1.6449, 0.95: 1.9600, 0.99: 2.5758}

# Student t critical values for degrees of freedom 1 to 30.
# T_TABLE[confidence][df - 1] is the value for that df.
T_TABLE = {
    0.90: [6.314, 2.920, 2.353, 2.132, 2.015, 1.943, 1.895, 1.860, 1.833, 1.812,
           1.796, 1.782, 1.771, 1.761, 1.753, 1.746, 1.740, 1.734, 1.729, 1.725,
           1.721, 1.717, 1.714, 1.711, 1.708, 1.706, 1.703, 1.701, 1.699, 1.697],
    0.95: [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228,
           2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086,
           2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042],
    0.99: [63.657, 9.925, 5.841, 4.604, 4.032, 3.707, 3.499, 3.355, 3.250, 3.169,
           3.106, 3.055, 3.012, 2.977, 2.947, 2.921, 2.898, 2.878, 2.861, 2.845,
           2.831, 2.819, 2.807, 2.797, 2.787, 2.779, 2.771, 2.763, 2.756, 2.750],
}


def sample_sd(values):
    """Sample standard deviation: sqrt(sum((x - mean)^2) / (n - 1)).
    Raise ValueError if there are fewer than 2 values."""
    # TODO
    raise NotImplementedError


def critical_value(df, confidence=0.95):
    """Return the t value from T_TABLE when 1 <= df <= 30, otherwise the Z value."""
    # TODO
    raise NotImplementedError


def mean_ci(values, confidence=0.95):
    """Return (low, high) for the mean: mean +/- critical_value(n - 1) * sd / sqrt(n).
    Fewer than 2 values: raise ValueError (sample_sd already does)."""
    # TODO
    raise NotImplementedError


def proportion_ci(successes, n, confidence=0.95):
    """Return (low, high) for a proportion: p +/- z * sqrt(p * (1 - p) / n).
    Use Z, not the t table. Raise ValueError if n < 1 or successes is not
    between 0 and n."""
    # TODO
    raise NotImplementedError


def read_column(path, column):
    """Read one numeric column of a CSV as a list of floats."""
    # TODO
    raise NotImplementedError
