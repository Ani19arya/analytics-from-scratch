"""Lesson 01 solution: mean, median, spread and skew, by hand."""
import csv
import math


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


def std_dev(values):
    values = list(values)
    m = mean(values)
    squared = 0.0
    for v in values:
        squared += (v - m) ** 2
    return math.sqrt(squared / len(values))


def percentile(values, p):
    if not 0 <= p <= 100:
        raise ValueError("p must be between 0 and 100")
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile of an empty list")
    rank = p / 100 * (len(ordered) - 1)
    low = math.floor(rank)
    high = math.ceil(rank)
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def histogram(values, width):
    values = list(values)
    if not values:
        return []
    counts = {}
    for v in values:
        start = math.floor(v / width) * width
        counts[start] = counts.get(start, 0) + 1
    first = math.floor(min(values) / width) * width
    last = math.floor(max(values) / width) * width
    bins = []
    start = first
    while start <= last:
        bins.append((start, counts.get(start, 0)))
        start += width
    return bins


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
    return {"n": len(pay), "mean": m, "median": med, "gap": m - med,
            "sd": std_dev(pay), "p25": percentile(pay, 25), "p75": percentile(pay, 75),
            "skew": skew_label(pay)}


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    for key, value in summarise(os.path.join(here, "..", "data", "postings.csv")).items():
        print(key, round(value, 2) if isinstance(value, float) else value)
