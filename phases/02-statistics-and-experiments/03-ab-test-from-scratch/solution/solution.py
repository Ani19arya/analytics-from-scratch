"""Lesson 03 solution: a two-proportion z-test from the formula, with a
sample ratio mismatch check and a confidence interval on the difference."""
import csv
import math


def normal_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def count_conversions(path):
    counts = {"A": [0, 0], "B": [0, 0]}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            c = counts[row["variant"]]
            c[0] += int(row["converted"])
            c[1] += 1
    return {k: (v[0], v[1]) for k, v in counts.items()}


def srm_check(n_a, n_b, expected_share_a=0.5):
    total = n_a + n_b
    if total == 0:
        raise ValueError("no users in either group")
    exp_a = total * expected_share_a
    exp_b = total - exp_a
    chi2 = (n_a - exp_a) ** 2 / exp_a + (n_b - exp_b) ** 2 / exp_b
    p_value = 2 * (1 - normal_cdf(math.sqrt(chi2)))
    return {"chi2": chi2, "p_value": p_value}


def two_proportion_ztest(conv_a, n_a, conv_b, n_b):
    if n_a <= 0 or n_b <= 0:
        raise ValueError("each group needs at least one user")
    p_a = conv_a / n_a
    p_b = conv_b / n_b
    lift = p_b - p_a
    p_pool = (conv_a + conv_b) / (n_a + n_b)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
    if se == 0:
        z, p_value = 0.0, 1.0
    else:
        z = lift / se
        p_value = 2 * (1 - normal_cdf(abs(z)))
    return {"p_a": p_a, "p_b": p_b, "lift": lift, "p_pool": p_pool,
            "se": se, "z": z, "p_value": p_value}


def diff_ci(conv_a, n_a, conv_b, n_b, z=1.96):
    if n_a <= 0 or n_b <= 0:
        raise ValueError("each group needs at least one user")
    p_a = conv_a / n_a
    p_b = conv_b / n_b
    se = math.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    lift = p_b - p_a
    return (lift - z * se, lift + z * se)


def decide(result, alpha=0.05, min_lift=0.0):
    if result["p_value"] < alpha and result["lift"] > 0 and result["lift"] >= min_lift:
        return "ship"
    return "do not ship"


if __name__ == "__main__":
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "experiment.csv")
    counts = count_conversions(path)
    (ca, na), (cb, nb) = counts["A"], counts["B"]
    print("A", ca, "/", na, "B", cb, "/", nb)
    print("srm", {k: round(v, 4) for k, v in srm_check(na, nb).items()})
    r = two_proportion_ztest(ca, na, cb, nb)
    print({k: round(v, 5) for k, v in r.items()})
    print("95% CI on the lift", [round(x, 4) for x in diff_ci(ca, na, cb, nb)])
    print("decision:", decide(r))
