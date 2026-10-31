"""Lesson 09: the chi-square test of independence, from scratch. Worked solution.

Uses only csv and math. Run from the lesson folder:
    python3 solution/solution.py
"""
import csv
import math
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EPS = 1e-15
MAX_ITER = 10000


def read_table(path):
    """Return (flows, observed): flows sorted by name, observed[i] = [completed, not_completed].
    Rows with a blank completed are skipped: their outcome is not known yet."""
    counts = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            value = row["completed"].strip()
            if value == "":
                continue
            cell = counts.setdefault(row["flow"], [0, 0])
            if int(value) == 1:
                cell[0] += 1
            else:
                cell[1] += 1
    flows = sorted(counts)
    return flows, [counts[name] for name in flows]


def check_table(observed):
    if len(observed) < 2 or any(len(row) != len(observed[0]) for row in observed) or len(observed[0]) < 2:
        raise ValueError("need a rectangular table with at least 2 rows and 2 columns")
    for row in observed:
        for value in row:
            if value < 0 or value != int(value):
                raise ValueError("cells must be whole counts, not rates or percentages")


def expected_counts(observed):
    check_table(observed)
    row_totals = [sum(row) for row in observed]
    col_totals = [sum(col) for col in zip(*observed)]
    n = sum(row_totals)
    if min(row_totals) == 0 or min(col_totals) == 0:
        raise ValueError("a row or column adds up to 0, so its expected counts are 0")
    return [[r * c / n for c in col_totals] for r in row_totals]


def chi_square_statistic(observed, expected):
    return sum((o - e) ** 2 / e for orow, erow in zip(observed, expected) for o, e in zip(orow, erow))


def degrees_of_freedom(rows, cols):
    return (rows - 1) * (cols - 1)


def lower_gamma_series(a, x):
    """Regularized lower incomplete gamma P(a, x) by its power series (good for x < a + 1)."""
    term = 1.0 / a
    total = term
    ap = a
    for _ in range(MAX_ITER):
        ap += 1
        term *= x / ap
        total += term
        if abs(term) < abs(total) * EPS:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def upper_gamma_fraction(a, x):
    """Regularized upper incomplete gamma Q(a, x) by a continued fraction, modified Lentz (good for x >= a + 1)."""
    tiny = 1e-300
    b = x + 1 - a
    c = 1 / tiny
    d = 1 / b
    h = d
    for i in range(1, MAX_ITER):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < EPS:
            break
    return h * math.exp(-x + a * math.log(x) - math.lgamma(a))


def chi2_sf(x, df):
    """P(chi-square with df degrees of freedom >= x) = Q(df / 2, x / 2)."""
    if df < 1:
        raise ValueError("degrees of freedom must be at least 1")
    if x <= 0:
        return 1.0
    a, half = df / 2, x / 2
    if half < a + 1:
        return 1.0 - lower_gamma_series(a, half)
    return upper_gamma_fraction(a, half)


def cramers_v(chi2, n, rows, cols):
    k = min(rows, cols) - 1
    if n <= 0 or k < 1:
        raise ValueError("need n > 0 and at least 2 rows and 2 columns")
    return math.sqrt(chi2 / (n * k))


def chi_square_test(observed):
    expected = expected_counts(observed)
    chi2 = chi_square_statistic(observed, expected)
    rows, cols = len(observed), len(observed[0])
    df = degrees_of_freedom(rows, cols)
    n = sum(sum(row) for row in observed)
    small = [(i, j) for i in range(rows) for j in range(cols) if expected[i][j] < 5]
    return {"chi2": chi2, "df": df, "p_value": chi2_sf(chi2, df), "cramers_v": cramers_v(chi2, n, rows, cols),
            "n": n, "expected": expected, "small_cells": small}


def summarise(path):
    flows, observed = read_table(path)
    r = chi_square_test(observed)
    out = {"flows": flows, "observed": observed,
           "rates": [round(c / (c + nc), 4) for c, nc in observed],
           "expected": [[round(v, 2) for v in row] for row in r["expected"]]}
    for key in ("chi2", "df", "p_value", "cramers_v", "n", "small_cells"):
        value = r[key]
        out[key] = round(value, 4) if isinstance(value, float) else value
    return out


if __name__ == "__main__":
    for key, value in summarise(os.path.join(HERE, "data", "signups.csv")).items():
        print(key, value)
