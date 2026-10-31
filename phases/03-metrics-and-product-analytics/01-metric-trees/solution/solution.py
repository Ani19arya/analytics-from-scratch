"""Lesson 01: metric trees. Worked answer.

revenue = visitors x conversion x average order value (AOV)
The split of a revenue change uses the logarithmic mean (LMDI).
"""
import csv
import math

FACTORS = ("visitors", "conversion", "aov")


def build_tree(visitors, orders, revenue):
    """Return the tree for one period as a dict with keys
    visitors, orders, revenue, conversion (orders / visitors), aov (revenue / orders).
    A ratio whose denominator is 0 is 0.0."""
    return {
        "visitors": visitors,
        "orders": orders,
        "revenue": revenue,
        "conversion": orders / visitors if visitors else 0.0,
        "aov": revenue / orders if orders else 0.0,
    }


def load_weeks(path, split_date, channel=None):
    """Sum visitors, orders and revenue for the days before split_date (prior)
    and on or after it (current). If channel is given, use only that channel.
    Return (prior_tree, current_tree)."""
    sums = {"prior": [0, 0, 0.0], "current": [0, 0, 0.0]}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if channel is not None and row["channel"] != channel:
                continue
            key = "prior" if row["date"] < split_date else "current"
            sums[key][0] += int(row["visitors"])
            sums[key][1] += int(row["orders"])
            sums[key][2] += float(row["revenue"])
    return build_tree(*sums["prior"]), build_tree(*sums["current"])


def log_mean(a, b):
    """The logarithmic mean of two positive numbers: (a - b) / (ln a - ln b),
    and a itself when a equals b (the limit of the formula)."""
    if a == b:
        return float(a)
    return (a - b) / (math.log(a) - math.log(b))


def decompose(prior, current):
    """Split the revenue change into the part from each factor (LMDI):
    effect_f = L(current_rev, prior_rev) * ln(current_f / prior_f).
    Return a dict with keys visitors, conversion, aov, total. The three effects sum to total.
    If revenue or any factor is 0 in either period, the logs are undefined, so every
    factor effect is None and only total is filled in."""
    total = current["revenue"] - prior["revenue"]
    result = {"total": total}
    values = [prior["revenue"], current["revenue"]] + [t[f] for t in (prior, current) for f in FACTORS]
    if any(v <= 0 for v in values):
        for f in FACTORS:
            result[f] = None
        return result
    weight = log_mean(current["revenue"], prior["revenue"])
    for f in FACTORS:
        result[f] = weight * math.log(current[f] / prior[f])
    return result


def main_driver(effects):
    """Return the factor name (visitors, conversion or aov) with the largest absolute effect.
    A tie goes to the factor listed first in FACTORS. None if the effects are None."""
    if any(effects[f] is None for f in FACTORS):
        return None
    best = FACTORS[0]
    for f in FACTORS[1:]:
        if abs(effects[f]) > abs(effects[best]):
            best = f
    return best


if __name__ == "__main__":
    import os
    data = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "daily_channels.csv")
    prior, current = load_weeks(data, "2026-10-12")
    for name, tree in (("prior", prior), ("current", current)):
        print("%-8s visitors %6d  orders %4d  revenue %9.2f  conversion %.4f  aov %.2f" % (
            name, tree["visitors"], tree["orders"], tree["revenue"], tree["conversion"], tree["aov"]))
    effects = decompose(prior, current)
    print({k: round(v, 2) for k, v in effects.items()}, "driver:", main_driver(effects))
    for ch in ("search", "email", "paid_social"):
        p, c = load_weeks(data, "2026-10-12", channel=ch)
        e = decompose(p, c)
        print("%-12s revenue change %9.2f  conversion %.4f -> %.4f  aov %.2f -> %.2f  driver: %s" % (
            ch, e["total"], p["conversion"], c["conversion"], p["aov"], c["aov"], main_driver(e)))
