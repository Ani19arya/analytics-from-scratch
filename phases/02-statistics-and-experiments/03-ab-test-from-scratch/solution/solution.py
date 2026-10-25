"""Lesson 03 solution: a two-proportion z-test from the formula."""
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


def two_proportion_ztest(conv_a, n_a, conv_b, n_b):
    p_a = conv_a / n_a
    p_b = conv_b / n_b
    lift = p_b - p_a
    p_pool = (conv_a + conv_b) / (n_a + n_b)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
    z = lift / se
    p_value = 2 * (1 - normal_cdf(abs(z)))
    return {"p_a": p_a, "p_b": p_b, "lift": lift, "p_pool": p_pool,
            "se": se, "z": z, "p_value": p_value}


def decide(result, alpha=0.05):
    if result["p_value"] < alpha and result["lift"] > 0:
        return "ship"
    return "do not ship"


if __name__ == "__main__":
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "experiment.csv")
    counts = count_conversions(path)
    (ca, na), (cb, nb) = counts["A"], counts["B"]
    r = two_proportion_ztest(ca, na, cb, nb)
    print("A", ca, "/", na, "B", cb, "/", nb)
    print({k: round(v, 5) for k, v in r.items()})
    print("decision:", decide(r))
