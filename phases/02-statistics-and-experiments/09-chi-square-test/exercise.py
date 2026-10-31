"""Lesson 09: the chi-square test of independence, from scratch. Your turn.

Rules: no `statistics`, `numpy`, `pandas` or `scipy` (the test checks this).
`csv` and `math` are fine; math.lgamma gives log(Gamma(a)).
Fill in every function marked TODO, then run: python3 test_lesson.py
"""
import csv
import math


def read_table(path):
    """Return (flows, observed): flow names sorted alphabetically, and
    observed[i] = [completed, not_completed] for flows[i].
    A blank completed means the outcome is not known yet: skip the row."""
    # TODO
    raise NotImplementedError


def expected_counts(observed):
    """Expected count of every cell if the row and column were unrelated:
    row total * column total / grand total.
    Raise ValueError unless the table is rectangular with at least 2 rows and
    2 columns of whole, non-negative counts (55.5 is a rate, not a count), and
    if any row or column adds up to 0."""
    # TODO
    raise NotImplementedError


def chi_square_statistic(observed, expected):
    """Sum over every cell of (observed - expected)^2 / expected."""
    # TODO
    raise NotImplementedError


def degrees_of_freedom(rows, cols):
    # TODO
    raise NotImplementedError


def chi2_sf(x, df):
    """P(X >= x) for a chi-square with df degrees of freedom. Return 1.0 for x <= 0.
    Raise ValueError if df < 1.

    It equals Q(df / 2, x / 2), the regularized upper incomplete gamma function.
    With a = df / 2 and h = x / 2:
    - if h < a + 1, use the series   P = exp(-h + a*log(h) - lgamma(a)) * sum_k h^k / (a (a+1) ... (a+k))
      and return 1 - P;
    - otherwise use the continued fraction for Q (modified Lentz method), whose
      terms are a_i = -i * (i - a) and b_i = h + 1 - a + 2i.
    Stop when a term changes the answer by less than 1e-15 relative."""
    # TODO
    raise NotImplementedError


def cramers_v(chi2, n, rows, cols):
    """Effect size from 0 (no association) to 1: sqrt(chi2 / (n * (min(rows, cols) - 1)))."""
    # TODO
    raise NotImplementedError


def chi_square_test(observed):
    """Return {"chi2", "df", "p_value", "cramers_v", "n", "expected", "small_cells"}.
    small_cells lists (row, column) for every cell whose EXPECTED count is below 5,
    in row order. Do not apply any continuity correction."""
    # TODO
    raise NotImplementedError


def summarise(path):
    """Return flows, observed, rates (completed share per flow, 4 decimals),
    expected (2 decimals), and chi2, df, p_value, cramers_v (4 decimals), n and
    small_cells for the signups file."""
    # TODO
    raise NotImplementedError
