"""Lesson 01 solution: mean, median and skew, by hand."""
import csv


def mean(values):
    values = list(values)
    if not values:
        raise ValueError("mean of an empty list")
    total = 0.0
    for v in values:
        total += v
    return total / len(values)


def median(values):
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        raise ValueError("median of an empty list")
    middle = n // 2
    if n % 2 == 1:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def skew_label(values, tolerance=0.01):
    m = mean(values)
    med = median(values)
    if m - med > tolerance * abs(med):
        return "right"
    if med - m > tolerance * abs(med):
        return "left"
    return "symmetric"


def read_pay(path):
    with open(path, newline="") as f:
        return [float(row["pay_mid"]) for row in csv.DictReader(f)]


def summarise(path):
    pay = read_pay(path)
    m = mean(pay)
    med = median(pay)
    return {"n": len(pay), "mean": m, "median": med,
            "gap": m - med, "skew": skew_label(pay)}


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    print(summarise(os.path.join(here, "..", "data", "postings.csv")))
