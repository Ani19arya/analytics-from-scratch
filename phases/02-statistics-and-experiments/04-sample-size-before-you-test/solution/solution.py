"""Lesson 04 solution: sample size for a two-proportion test, from the formula."""
import csv
import math


def normal_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def z_quantile(p):
    if not 0 < p < 1:
        raise ValueError("p must be between 0 and 1")
    low, high = -10.0, 10.0
    for _ in range(200):
        mid = (low + high) / 2
        if normal_cdf(mid) < p:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def sample_size_per_group(p1, p2, alpha=0.05, power=0.80):
    if p1 == p2:
        raise ValueError("p1 and p2 must differ")
    z_a = z_quantile(1 - alpha / 2)
    z_b = z_quantile(power)
    p_bar = (p1 + p2) / 2
    top = (z_a * math.sqrt(2 * p_bar * (1 - p_bar))
           + z_b * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    return math.ceil(top / (p2 - p1) ** 2)


def sample_size_for_lift(baseline, relative_lift, alpha=0.05, power=0.80):
    return sample_size_per_group(baseline, baseline * (1 + relative_lift), alpha, power)


def weeks_needed(n_per_group, weekly_visitors, groups=2):
    return math.ceil(n_per_group * groups / weekly_visitors)


def plan(path, relative_lift, alpha=0.05, power=0.80):
    out = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            base = float(row["baseline_rate"])
            n = sample_size_for_lift(base, relative_lift, alpha, power)
            out.append({"page": row["page"], "baseline_rate": base, "n_per_group": n,
                        "weeks": weeks_needed(n, int(row["weekly_visitors"]))})
    return out


if __name__ == "__main__":
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "pages.csv")
    for lift in (0.20, 0.10, 0.05):
        print("relative lift", lift)
        for r in plan(path, lift):
            print("  ", r)
