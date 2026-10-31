"""Lesson 05 solution: probability and distributions by simulation."""
import csv
import math
import random


def check_rate(p):
    if not 0 <= p <= 1:
        raise ValueError("p must be between 0 and 1")


def count_buyers(path):
    """Return (visitors, buyers) from the bought column of the CSV."""
    n = k = 0
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            n += 1
            k += int(row["bought"])
    return n, k


def simulate_counts(n, p, runs, seed):
    """Pretend `runs` days. On each day n visitors each buy with chance p.
    Return the list of buyer counts, one per day."""
    check_rate(p)
    if n < 0 or runs < 0:
        raise ValueError("n and runs must be 0 or more")
    rng = random.Random(seed)
    counts = []
    for _ in range(runs):
        buyers = 0
        for _ in range(n):
            if rng.random() < p:
                buyers += 1
        counts.append(buyers)
    return counts


def share_at_least(counts, k):
    if not counts:
        raise ValueError("no simulated days")
    return sum(1 for c in counts if c >= k) / len(counts)


def share_exactly(counts, k):
    if not counts:
        raise ValueError("no simulated days")
    return sum(1 for c in counts if c == k) / len(counts)


def binom_pmf(k, n, p):
    """P(X = k) for X ~ Binomial(n, p): comb(n, k) * p^k * (1 - p)^(n - k)."""
    check_rate(p)
    if k < 0 or k > n:
        return 0.0
    return math.comb(n, k) * p ** k * (1 - p) ** (n - k)


def binom_at_least(k, n, p):
    """P(X >= k): add up the exact probabilities from k to n."""
    check_rate(p)
    if k <= 0:
        return 1.0
    return sum(binom_pmf(j, n, p) for j in range(k, n + 1))


def simulation_se(share, runs):
    """How far a simulated share typically lands from the exact one."""
    if runs < 1:
        raise ValueError("runs must be at least 1")
    return math.sqrt(share * (1 - share) / runs)


def summarise(path, p=0.10, runs=10000, seed=1):
    n, k = count_buyers(path)
    counts = simulate_counts(n, p, runs, seed)
    sim = share_at_least(counts, k)
    return {"visitors": n, "buyers": k, "expected": n * p, "sd": math.sqrt(n * p * (1 - p)),
            "p_exactly": binom_pmf(k, n, p), "p_at_least": binom_at_least(k, n, p),
            "sim_at_least": sim, "sim_se": simulation_se(sim, runs)}


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    for key, value in summarise(os.path.join(here, "..", "data", "visitors.csv")).items():
        print(key, round(value, 4) if isinstance(value, float) else value)
