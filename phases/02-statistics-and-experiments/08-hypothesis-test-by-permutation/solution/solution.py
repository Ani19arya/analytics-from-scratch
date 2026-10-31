"""Lesson 08: a permutation test, written from scratch. Worked solution.

Uses only csv, itertools, math and random. Run from the lesson folder:
    python3 solution/solution.py
"""
import csv
import itertools
import math
import os
import random

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOL = 1e-9
ALTERNATIVES = ("two-sided", "greater", "less")


def read_groups(path):
    """Return {"control": [values], "side_dish": [values]} in file order. Skip blank values."""
    groups = {"control": [], "side_dish": []}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            value = row["order_value"].strip()
            if value == "":
                continue
            groups[row["group"]].append(float(value))
    return groups


def mean(values):
    if not values:
        raise ValueError("mean of an empty list")
    return sum(values) / len(values)


def mean_diff(a, b):
    """mean(b) - mean(a): the new group minus the control group."""
    return mean(b) - mean(a)


def is_extreme(diff, observed, alternative):
    """Is a shuffled diff at least as extreme as the observed one? TOL absorbs float noise."""
    if alternative == "two-sided":
        return abs(diff) >= abs(observed) - TOL
    if alternative == "greater":
        return diff >= observed - TOL
    if alternative == "less":
        return diff <= observed + TOL
    raise ValueError("alternative must be one of %s" % ", ".join(ALTERNATIVES))


def permutation_test(a, b, n_perm=10000, seed=0, alternative="two-sided"):
    if not a or not b:
        raise ValueError("both groups need at least one value")
    if n_perm < 1:
        raise ValueError("n_perm must be at least 1")
    if alternative not in ALTERNATIVES:
        raise ValueError("alternative must be one of %s" % ", ".join(ALTERNATIVES))
    observed = mean_diff(a, b)
    rng = random.Random(seed)
    pooled = list(a) + list(b)
    k = len(a)
    extreme = 0
    for _ in range(n_perm):
        rng.shuffle(pooled)
        if is_extreme(mean_diff(pooled[:k], pooled[k:]), observed, alternative):
            extreme += 1
    return {"observed": observed, "extreme": extreme, "n_perm": n_perm,
            "p_value": (extreme + 1) / (n_perm + 1)}


def exact_test(a, b, alternative="two-sided", max_splits=200000):
    if not a or not b:
        raise ValueError("both groups need at least one value")
    if alternative not in ALTERNATIVES:
        raise ValueError("alternative must be one of %s" % ", ".join(ALTERNATIVES))
    pooled = list(a) + list(b)
    total = math.comb(len(pooled), len(a))
    if total > max_splits:
        raise ValueError("%d splits is too many to enumerate; use permutation_test" % total)
    observed = mean_diff(a, b)
    extreme = 0
    for idx in itertools.combinations(range(len(pooled)), len(a)):
        chosen = set(idx)
        new_a = [pooled[i] for i in idx]
        new_b = [pooled[i] for i in range(len(pooled)) if i not in chosen]
        if is_extreme(mean_diff(new_a, new_b), observed, alternative):
            extreme += 1
    return {"observed": observed, "extreme": extreme, "splits": total, "p_value": extreme / total}


def summarise(orders_path, pilot_path, n_perm=10000, seed=0):
    g = read_groups(orders_path)
    two = permutation_test(g["control"], g["side_dish"], n_perm, seed, "two-sided")
    pilot = read_groups(pilot_path)
    exact = exact_test(pilot["control"], pilot["side_dish"])
    approx = permutation_test(pilot["control"], pilot["side_dish"], n_perm, seed)
    return {
        "n_control": len(g["control"]),
        "n_side_dish": len(g["side_dish"]),
        "observed": round(two["observed"], 4),
        "p_two_sided": round(two["p_value"], 4),
        "pilot_observed": round(exact["observed"], 4),
        "pilot_exact_p": round(exact["p_value"], 4),
        "pilot_splits": exact["splits"],
        "pilot_permutation_p": round(approx["p_value"], 4),
    }


if __name__ == "__main__":
    s = summarise(os.path.join(HERE, "data", "orders.csv"), os.path.join(HERE, "data", "pilot.csv"))
    for key, value in s.items():
        print(key, value)
