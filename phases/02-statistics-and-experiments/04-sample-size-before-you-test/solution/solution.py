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
    if relative_lift == 0:
        raise ValueError("relative_lift must not be 0")
    return sample_size_per_group(baseline, baseline * (1 + relative_lift), alpha, power)


def weeks_needed(n_per_group, weekly_visitors, groups=2, min_weeks=1):
    if weekly_visitors <= 0:
        raise ValueError("weekly_visitors must be positive")
    return max(math.ceil(n_per_group * groups / weekly_visitors), min_weeks)


def plan(path, relative_lift, alpha=0.05, power=0.80, min_weeks=2):
    out = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            base = float(row["baseline_rate"])
            n = sample_size_for_lift(base, relative_lift, alpha, power)
            weekly = int(row["weekly_visitors"])
            out.append({"page": row["page"], "baseline_rate": base, "weekly_visitors": weekly,
                        "n_per_group": n, "weeks": weeks_needed(n, weekly, min_weeks=min_weeks)})
    return out


if __name__ == "__main__":
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "pages.csv")
    plans = {lift: plan(path, lift) for lift in (0.20, 0.10, 0.05)}
    print("%-9s %8s %7s %9s %9s %9s %6s %6s %6s" % ("page", "baseline", "visits", "n at 20%", "n at 10%",
                                                    "n at 5%", "wk 20%", "wk 10%", "wk 5%"))
    for i, row in enumerate(plans[0.20]):
        ns = [plans[lift][i]["n_per_group"] for lift in (0.20, 0.10, 0.05)]
        weeks = [plans[lift][i]["weeks"] for lift in (0.20, 0.10, 0.05)]
        print("%-9s %7.1f%% %7d %9d %9d %9d %6d %6d %6d"
              % ((row["page"], row["baseline_rate"] * 100, row["weekly_visitors"]) + tuple(ns) + tuple(weeks)))
