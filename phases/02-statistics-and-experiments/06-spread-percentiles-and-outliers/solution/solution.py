"""Lesson 06 solution: outliers, box plots and robust summaries, by hand."""
import csv
import math


def percentile(values, p):
    """Inclusive method (Excel PERCENTILE.INC, pandas and numpy default, PostgreSQL
    percentile_cont, statistics.quantiles(method="inclusive")):
    rank = p / 100 * (n - 1) on the sorted list, interpolating between neighbours."""
    if not 0 <= p <= 100:
        raise ValueError("p must be between 0 and 100")
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile of an empty list")
    rank = p / 100 * (len(ordered) - 1)
    low = math.floor(rank)
    high = math.ceil(rank)
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def median(values):
    return percentile(values, 50)


def quartiles(values):
    return percentile(values, 25), percentile(values, 50), percentile(values, 75)


def iqr_fences(values, k=1.5):
    q1, _, q3 = quartiles(values)
    iqr = q3 - q1
    return q1 - k * iqr, q3 + k * iqr


def flag_outliers(values, k=1.5):
    low, high = iqr_fences(values, k)
    return sorted(v for v in values if v < low or v > high)


def mad(values):
    """Median absolute deviation: the median distance from the median."""
    med = median(values)
    return median([abs(v - med) for v in values])


def mean(values):
    values = list(values)
    if not values:
        raise ValueError("mean of an empty list")
    return sum(values) / len(values)


def sample_sd(values):
    values = list(values)
    if len(values) < 2:
        raise ValueError("an SD needs at least 2 values")
    m = mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def box_plot_stats(values, k=1.5):
    q1, med, q3 = quartiles(values)
    low, high = iqr_fences(values, k)
    inside = [v for v in values if low <= v <= high]
    return {"q1": q1, "median": med, "q3": q3, "iqr": q3 - q1, "low_fence": low, "high_fence": high,
            "low_whisker": min(inside), "high_whisker": max(inside),
            "outliers": sorted(v for v in values if v < low or v > high)}


def read_rows(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["response_id"] = int(row["response_id"])
        row["years_experience"] = int(row["years_experience"])
        row["base_pay"] = float(row["base_pay"])
    return rows


def entry_errors(rows, floor=1000):
    """Rows whose yearly pay is below `floor`: typed in thousands, not real salaries."""
    return sorted(r["response_id"] for r in rows if r["base_pay"] < floor)


def describe(values):
    return {"n": len(values), "mean": mean(values), "sd": sample_sd(values), "median": median(values),
            "iqr": percentile(values, 75) - percentile(values, 25), "mad": mad(values)}


def summarise(path):
    rows = read_rows(path)
    pay = [r["base_pay"] for r in rows]
    errors = set(entry_errors(rows))
    cleaned = [r["base_pay"] for r in rows if r["response_id"] not in errors]
    flagged = set(flag_outliers(pay))
    trimmed = [v for v in pay if v not in flagged]
    return {"errors": sorted(errors), "flagged": len([v for v in pay if v in flagged]),
            "box": box_plot_stats(pay), "all": describe(pay), "cleaned": describe(cleaned),
            "trimmed": describe(trimmed)}


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    result = summarise(os.path.join(here, "..", "data", "salaries.csv"))
    print("entry errors:", result["errors"], " flagged by the fences:", result["flagged"])
    box = result["box"]
    print("box: q1 %.0f median %.0f q3 %.0f iqr %.0f fences %.1f to %.1f whiskers %.0f to %.0f"
          % (box["q1"], box["median"], box["q3"], box["iqr"], box["low_fence"], box["high_fence"],
             box["low_whisker"], box["high_whisker"]))
    for name in ("all", "cleaned", "trimmed"):
        d = result[name]
        print("%-8s n %3d  mean %8.0f  sd %7.0f  median %7.0f  iqr %6.0f  mad %6.0f"
              % (name, d["n"], d["mean"], d["sd"], d["median"], d["iqr"], d["mad"]))
