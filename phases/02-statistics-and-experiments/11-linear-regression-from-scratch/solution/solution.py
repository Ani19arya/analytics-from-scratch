"""Lesson 11: simple linear regression from the formulas. Worked solution.

Uses only csv and math. Run from the lesson folder:
    python3 solution/solution.py
"""
import csv
import math
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_members(path):
    """Return (visits, spend) as two lists in file order. Skip members whose
    spend_30d is blank: their spend is unknown, not 0."""
    xs, ys = [], []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if row["spend_30d"].strip() == "":
                continue
            xs.append(int(row["visits_30d"]))
            ys.append(float(row["spend_30d"]))
    return xs, ys


def fit_line(xs, ys):
    """Ordinary least squares: slope = Sxy / Sxx, intercept = mean_y - slope * mean_x."""
    if len(xs) != len(ys):
        raise ValueError("xs and ys must have the same length")
    if len(xs) < 2:
        raise ValueError("need at least 2 points")
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        raise ValueError("x does not vary, so no slope can be estimated")
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    return {"slope": slope, "intercept": my - slope * mx}


def predict(fit, x):
    return fit["intercept"] + fit["slope"] * x


def residuals(xs, ys, fit):
    return [y - predict(fit, x) for x, y in zip(xs, ys)]


def r_squared(xs, ys, fit):
    """1 - SSE / SST: the share of the variation in y around its mean that the line accounts for."""
    my = sum(ys) / len(ys)
    sst = sum((y - my) ** 2 for y in ys)
    if sst == 0:
        raise ValueError("y does not vary, so R squared is undefined")
    sse = sum(e ** 2 for e in residuals(xs, ys, fit))
    return 1 - sse / sst


def slope_se(xs, ys, fit):
    """Standard error of the slope: sqrt(SSE / (n - 2)) / sqrt(Sxx)."""
    n = len(xs)
    if n < 3:
        raise ValueError("need at least 3 points: 2 are used up by the slope and intercept")
    mx = sum(xs) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sse = sum(e ** 2 for e in residuals(xs, ys, fit))
    return math.sqrt(sse / (n - 2)) / math.sqrt(sxx)


def slope_ci(slope, se, crit=1.96):
    return (slope - crit * se, slope + crit * se)


def summarise(path):
    xs, ys = read_members(path)
    fit = fit_line(xs, ys)
    se = slope_se(xs, ys, fit)
    low, high = slope_ci(fit["slope"], se)
    return {
        "n": len(xs),
        "slope": round(fit["slope"], 4),
        "intercept": round(fit["intercept"], 4),
        "r_squared": round(r_squared(xs, ys, fit), 4),
        "slope_se": round(se, 4),
        "slope_ci": (round(low, 4), round(high, 4)),
        "residual_sd": round(math.sqrt(sum(e ** 2 for e in residuals(xs, ys, fit)) / (len(xs) - 2)), 4),
    }


if __name__ == "__main__":
    for key, value in summarise(os.path.join(HERE, "data", "members.csv")).items():
        print(key, value)
