"""Lesson 14: ratio metrics and the delta method. Worked solution.
Uses only csv and math. Run from the lesson folder:
    python3 solution/solution.py
"""
import csv
import math
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Z95 = 1.959963984540054


def read_users(path):
    """{variant: [(applications, replies), ...]} with one pair per user, in file order."""
    groups = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            groups.setdefault(row["variant"], []).append((int(row["applications"]), int(row["replies"])))
    return groups


def ratio(pairs):
    """Total replies / total applications."""
    denominator = sum(a for a, _ in pairs)
    if denominator == 0:
        raise ValueError("no applications, so the ratio is undefined")
    return sum(r for _, r in pairs) / denominator


def naive_var(pairs):
    """Variance of the ratio if every application were an independent coin flip:
    R (1 - R) / total applications. Wrong when users send many applications."""
    r = ratio(pairs)
    return r * (1 - r) / sum(a for a, _ in pairs)


def delta_var(pairs):
    """Delta method variance of total replies / total applications, with the
    user as the independent unit:
        (var_r - 2 R cov_ra + R^2 var_a) / (n * mean_a^2)
    with sample variances and covariance (divide by n - 1)."""
    n = len(pairs)
    if n < 2:
        raise ValueError("need at least two users")
    r = ratio(pairs)
    mean_a = sum(a for a, _ in pairs) / n
    mean_r = sum(x for _, x in pairs) / n
    var_a = sum((a - mean_a) ** 2 for a, _ in pairs) / (n - 1)
    var_r = sum((x - mean_r) ** 2 for _, x in pairs) / (n - 1)
    cov = sum((a - mean_a) * (x - mean_r) for a, x in pairs) / (n - 1)
    return max(0.0, (var_r - 2 * r * cov + r * r * var_a) / (n * mean_a ** 2))


def normal_cdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def compare(control, treatment, method="delta"):
    """Treatment ratio minus control ratio, with method "delta" or "naive".
    Returns {"control", "treatment", "diff", "se", "z", "p_value", "ci"}."""
    if method not in ("delta", "naive"):
        raise ValueError("method must be 'delta' or 'naive'")
    var = delta_var if method == "delta" else naive_var
    rc, rt = ratio(control), ratio(treatment)
    diff = rt - rc
    se = math.sqrt(var(control) + var(treatment))
    if se == 0:
        z, p = 0.0, 1.0
    else:
        z = diff / se
        p = min(1.0, 2 * (1 - normal_cdf(abs(z))))
    return {"control": rc, "treatment": rt, "diff": diff, "se": se, "z": z, "p_value": p,
            "ci": (diff - Z95 * se, diff + Z95 * se)}


def summarise(path):
    groups = read_users(path)
    c, t = groups["control"], groups["quick_apply"]
    naive = compare(c, t, "naive")
    delta = compare(c, t, "delta")
    return {
        "users": {"control": len(c), "quick_apply": len(t)},
        "applications": {"control": sum(a for a, _ in c), "quick_apply": sum(a for a, _ in t)},
        "naive": naive,
        "delta": delta,
        "design_effect": (delta["se"] / naive["se"]) ** 2,
    }


if __name__ == "__main__":
    s = summarise(os.path.join(HERE, "data", "users.csv"))
    print("users", s["users"], "applications", s["applications"])
    for name in ("naive", "delta"):
        x = s[name]
        print("%-5s control %.4f  quick_apply %.4f  diff %+.4f  se %.4f  z %+.2f  p %.4f  ci (%+.4f, %+.4f)" % (
            name, x["control"], x["treatment"], x["diff"], x["se"], x["z"], x["p_value"], x["ci"][0], x["ci"][1]))
    print("design_effect %.2f" % s["design_effect"])
