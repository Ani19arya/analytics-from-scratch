"""Lesson 02 solution: confidence intervals by hand.
"""
import csv
import math

# Two-sided critical values. Z is the normal distribution.
Z = {0.90: 1.6449, 0.95: 1.9600, 0.99: 2.5758}

# Student t critical values for degrees of freedom 1 to 30.
# T_TABLE[confidence][df - 1] is the value for that df.
T_TABLE = {
    0.90: [6.314, 2.920, 2.353, 2.132, 2.015, 1.943, 1.895, 1.860, 1.833, 1.812,
           1.796, 1.782, 1.771, 1.761, 1.753, 1.746, 1.740, 1.734, 1.729, 1.725,
           1.721, 1.717, 1.714, 1.711, 1.708, 1.706, 1.703, 1.701, 1.699, 1.697],
    0.95: [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228,
           2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086,
           2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042],
    0.99: [63.657, 9.925, 5.841, 4.604, 4.032, 3.707, 3.499, 3.355, 3.250, 3.169,
           3.106, 3.055, 3.012, 2.977, 2.947, 2.921, 2.898, 2.878, 2.861, 2.845,
           2.831, 2.819, 2.807, 2.797, 2.787, 2.779, 2.771, 2.763, 2.756, 2.750],
}


def sample_sd(values):
    values = list(values)
    n = len(values)
    if n < 2:
        raise ValueError("need at least 2 values")
    mean = sum(values) / n
    squared = sum((x - mean) ** 2 for x in values)
    return math.sqrt(squared / (n - 1))


def critical_value(df, confidence=0.95):
    if 1 <= df <= 30:
        return T_TABLE[confidence][df - 1]
    return Z[confidence]


def mean_ci(values, confidence=0.95):
    values = list(values)
    n = len(values)
    mean = sum(values) / n
    se = sample_sd(values) / math.sqrt(n)
    margin = critical_value(n - 1, confidence) * se
    return (mean - margin, mean + margin)


def proportion_ci(successes, n, confidence=0.95):
    p = successes / n
    se = math.sqrt(p * (1 - p) / n)
    margin = Z[confidence] * se
    return (p - margin, p + margin)


def read_column(path, column):
    with open(path, newline="") as f:
        return [float(row[column]) for row in csv.DictReader(f)]


if __name__ == "__main__":
    import os
    data = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    orders = read_column(os.path.join(data, "orders.csv"), "order_value")
    answers = read_column(os.path.join(data, "survey.csv"), "would_reorder")
    print("orders n", len(orders), "mean", round(sum(orders) / len(orders), 2),
          "sd", round(sample_sd(orders), 2), "95% CI", [round(x, 2) for x in mean_ci(orders)])
    k = int(sum(answers))
    print("survey", k, "of", len(answers), "95% CI", [round(x, 4) for x in proportion_ci(k, len(answers))],
          "99% CI", [round(x, 4) for x in proportion_ci(k, len(answers), 0.99)])
