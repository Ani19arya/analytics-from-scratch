"""Lesson 15: variance reduction with CUPED. Worked solution.
Uses only csv and math. Run from the lesson folder:
    python3 solution/solution.py
"""
import csv
import math
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Z95 = 1.959963984540054
COVARIATES = ("pre_spend", "test_sessions")


def read_users(path):
    """One dict per user: variant, pre_spend (float, or None when blank),
    spend (float), test_sessions (int)."""
    users = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            pre = row["pre_spend"].strip()
            users.append({"variant": row["variant"],
                          "pre_spend": float(pre) if pre else None,
                          "spend": float(row["spend"]),
                          "test_sessions": int(row["test_sessions"])})
    return users


def mean(values):
    if not values:
        raise ValueError("mean of an empty list")
    return sum(values) / len(values)


def sample_var(values):
    if len(values) < 2:
        raise ValueError("need at least two values")
    m = mean(values)
    return sum((v - m) ** 2 for v in values) / (len(values) - 1)


def fill_missing(xs):
    """Replace None with the mean of the values that are present."""
    present = [x for x in xs if x is not None]
    if not present:
        raise ValueError("every value is missing")
    m = mean(present)
    return [m if x is None else x for x in xs]


def theta(xs, ys):
    """cov(x, y) / var(x): the slope that removes the most variance from y."""
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("need two lists of the same length, at least 2")
    mx, my = mean(xs), mean(ys)
    var_x = sum((x - mx) ** 2 for x in xs)
    if var_x == 0:
        raise ValueError("x does not vary")
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / var_x


def cuped_adjust(xs, ys, t):
    """y - t * (x - mean(x)): same mean as y, less variance."""
    mx = mean(xs)
    return [y - t * (x - mx) for x, y in zip(xs, ys)]


def normal_cdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def diff_in_means(control, treatment):
    """Treatment mean minus control mean, unpooled standard error.
    Returns {"diff", "se", "p_value", "ci"}."""
    diff = mean(treatment) - mean(control)
    se = math.sqrt(sample_var(control) / len(control) + sample_var(treatment) / len(treatment))
    p = 1.0 if se == 0 else min(1.0, 2 * (1 - normal_cdf(abs(diff / se))))
    return {"diff": diff, "se": se, "p_value": p, "ci": (diff - Z95 * se, diff + Z95 * se)}


def summarise(path, covariate="pre_spend"):
    """Raw and CUPED comparisons of spend, shelf minus control."""
    if covariate not in COVARIATES:
        raise ValueError("unknown covariate")
    users = read_users(path)
    xs = fill_missing([u[covariate] for u in users])
    ys = [u["spend"] for u in users]
    t = theta(xs, ys)
    adjusted = cuped_adjust(xs, ys, t)
    groups = {"control": ([], []), "shelf": ([], [])}
    for u, y, a in zip(users, ys, adjusted):
        groups[u["variant"]][0].append(y)
        groups[u["variant"]][1].append(a)
    raw = diff_in_means(groups["control"][0], groups["shelf"][0])
    cuped = diff_in_means(groups["control"][1], groups["shelf"][1])
    share = (cuped["se"] / raw["se"]) ** 2
    return {"n": {k: len(v[0]) for k, v in groups.items()},
            "missing_covariate": sum(1 for u in users if u[covariate] is None),
            "theta": t, "raw": raw, "cuped": cuped,
            "variance_reduction": 1 - share, "users_needed_share": share}


if __name__ == "__main__":
    path = os.path.join(HERE, "data", "users.csv")
    for cov in COVARIATES:
        s = summarise(path, cov)
        print("covariate", cov, "n", s["n"], "missing", s["missing_covariate"], "theta %.4f" % s["theta"])
        for name in ("raw", "cuped"):
            x = s[name]
            print("  %-5s diff %+.2f  se %.2f  p %.4f  ci (%+.2f, %+.2f)" % (
                name, x["diff"], x["se"], x["p_value"], x["ci"][0], x["ci"][1]))
        print("  variance_reduction %.3f  users_needed_share %.3f" % (s["variance_reduction"], s["users_needed_share"]))
