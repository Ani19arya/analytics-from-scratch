"""Lesson 05: probability and distributions by simulation. Your turn.

Rules: no `statistics`, `numpy`, `pandas` or `scipy` (the test checks this).
`csv`, `math` and `random` are fine. Use random.Random(seed), never the shared
module-level functions such as random.random(), so the same seed always gives
the same answer.
Fill in every function marked TODO, then run: python3 test_lesson.py
"""
import csv
import math
import random


def count_buyers(path):
    """Return (visitors, buyers): the number of rows, and how many have bought = 1."""
    # TODO
    raise NotImplementedError


def simulate_counts(n, p, runs, seed):
    """Pretend `runs` days. On each day, n visitors each buy with chance p:
    a visitor buys when rng.random() < p, with rng = random.Random(seed) made once.
    Return a list of `runs` integers, the number of buyers on each pretend day.
    Raise ValueError if p is outside 0 to 1, or n or runs is negative."""
    # TODO
    raise NotImplementedError


def share_at_least(counts, k):
    """Share of the simulated days with k or MORE buyers. Raise ValueError if counts is empty."""
    # TODO
    raise NotImplementedError


def share_exactly(counts, k):
    """Share of the simulated days with EXACTLY k buyers. Raise ValueError if counts is empty."""
    # TODO
    raise NotImplementedError


def binom_pmf(k, n, p):
    """Exact P(X = k) when X counts buyers among n visitors who each buy with chance p:
    math.comb(n, k) * p**k * (1 - p)**(n - k). Return 0.0 when k < 0 or k > n.
    Raise ValueError if p is outside 0 to 1."""
    # TODO
    raise NotImplementedError


def binom_at_least(k, n, p):
    """Exact P(X >= k): the sum of binom_pmf(j, n, p) for j from k to n.
    Return 1.0 when k <= 0 (every day has at least 0 buyers)."""
    # TODO
    raise NotImplementedError


def simulation_se(share, runs):
    """Standard error of a share estimated from `runs` simulated days:
    sqrt(share * (1 - share) / runs). Raise ValueError if runs < 1."""
    # TODO
    raise NotImplementedError


def summarise(path, p=0.10, runs=10000, seed=1):
    """Return a dict with keys visitors, buyers, expected (n * p), sd (sqrt(n * p * (1 - p))),
    p_exactly, p_at_least (both exact), sim_at_least (from simulate_counts) and sim_se."""
    # TODO
    raise NotImplementedError
