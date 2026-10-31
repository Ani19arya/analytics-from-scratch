"""Exercise 07-09: the statistics interview round.

load, normal_cdf, z_quantile and conversions are done for you. Fill in two_proportion_z,
power, n_per_group, rates_by_segment and simpson_reversal, and give a verdict for each
statement in VERDICTS. Run: python3 test_lesson.py

Three questions on two tables:
1. Is the new checkout page better? A two-proportion z-test and its p-value.
2. Was the test big enough? Power for the lift the team cares about, and the users needed.
3. Coupon customers reorder less: should coupons stop? Rates by customer type (Simpson's paradox).
"""
import csv
import math
import os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
LIFT_THAT_MATTERS = 0.015  # 1.5 percentage points, the smallest lift worth shipping

# The interviewer's statements. True or False for each.
STATEMENTS = {
    1: "p = 0.30 means there is a 30% chance the new page makes no difference.",
    2: "p = 0.30 means: if the page made no difference, a gap at least this large, in either direction, would turn up in about 30% of tests like this one.",
    3: "The result is not significant, so the new page does not work.",
    4: "If a test has 20% power for a 1.5 point lift, it misses a real lift of that size about 80% of the time.",
    5: "Checking the p-value every day and stopping on the first day it is below 0.05 keeps the false positive rate at 5%.",
    6: "To halve the margin of error you need about four times as many users.",
    7: "A p-value of 0.001 means the effect is large.",
    8: "Coupon customers reorder less overall, so coupons cause fewer reorders.",
}
# TODO: replace each None with True or False.
VERDICTS = {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None, 8: None}


def load(name, data_dir=DATA):
    with open(os.path.join(data_dir, name), newline="") as f:
        return list(csv.DictReader(f))


def normal_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def z_quantile(p):
    """The z with normal_cdf(z) = p, by bisection."""
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


def conversions(rows):
    """{group: (converted, users)} from experiment rows."""
    out = {}
    for r in rows:
        x, n = out.get(r["group"], (0, 0))
        out[r["group"]] = (x + int(r["converted"]), n + 1)
    return out


def two_proportion_z(x1, n1, x2, n2):
    """Compare group 2 with group 1. Returns (difference in points, z, two-sided p-value).
    difference = 100 * (x2/n2 - x1/n1). The standard error uses the pooled rate
    (x1 + x2) / (n1 + n2), because the test asks how surprising the gap is if both groups
    share one rate. When every user or no user converted, the gap is 0: z = 0.0, p = 1.0.
    A group with no users raises ValueError."""
    # TODO
    raise NotImplementedError


def power(p1, p2, n, alpha=0.05):
    """Chance that a two-sided test at alpha, with n users per group, finds the gap
    between true rates p1 and p2 (normal approximation, the far tail ignored):
    Phi( (|p2 - p1| * sqrt(n) - z_a * sqrt(2 * pbar * (1 - pbar))) / sqrt(p1(1-p1) + p2(1-p2)) )
    with z_a = z_quantile(1 - alpha/2) and pbar = (p1 + p2) / 2. p1 == p2 raises ValueError."""
    # TODO: use z_quantile and normal_cdf.
    raise NotImplementedError


def n_per_group(p1, p2, target_power=0.80, alpha=0.05):
    """Users per group for target_power: the formula from lesson 02-04, rounded up."""
    # TODO: z for 1 - alpha/2 and z for target_power, then round up with math.ceil.
    raise NotImplementedError


def rates_by_segment(rows, segment, group, outcome):
    """{segment value or "all": {group value: (successes, count, rate)}}.
    outcome holds 0 or 1. rate is successes / count, or None when count is 0."""
    # TODO: count each row twice, once in its own segment and once in "all".
    raise NotImplementedError


def simpson_reversal(table, a, b):
    """True when the gap rate(b) - rate(a) has one sign in "all" and the opposite sign in
    every other segment. A segment missing a or b, with no users, or with a gap of exactly 0
    means no reversal (False)."""
    # TODO
    raise NotImplementedError


def main():
    groups = conversions(load("experiment.csv"))
    (xc, nc), (xt, nt) = groups["control"], groups["treatment"]
    diff, z, p = two_proportion_z(xc, nc, xt, nt)
    print("control %d/%d, treatment %d/%d: %+.1f points, z = %.2f, p = %.3f" % (xc, nc, xt, nt, diff, z, p))
    base = xc / nc
    n = min(nc, nt)
    print("power for +1.5 points at %d per group: %.2f" % (n, power(base, base + LIFT_THAT_MATTERS, n)))
    print("users per group for 80%% power: %d" % n_per_group(base, base + LIFT_THAT_MATTERS))
    table = rates_by_segment(load("coupons.csv"), "customer_type", "coupon", "reordered")
    for seg in ("all", "new", "returning"):
        print(seg, table[seg])
    print("reversal:", simpson_reversal(table, "no", "yes"))


if __name__ == "__main__":
    main()
