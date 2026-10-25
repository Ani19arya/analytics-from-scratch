"""Lesson 01: metric trees. Worked answer.

revenue = visitors x conversion x average order value (AOV)
"""
import csv
import math

FACTORS = ("visitors", "conversion", "aov")


def build_tree(visitors, orders, revenue):
    """Return the tree for one period as a dict with keys
    visitors, orders, revenue, conversion (orders / visitors), aov (revenue / orders)."""
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


def decompose(prior, current):
    """Split the revenue change into the part from each factor with the log method:
    effect_f = total_change * ln(current_f / prior_f) / ln(current_rev / prior_rev).
    Return a dict with keys visitors, conversion, aov, total. The three effects sum to total."""
    total = current["revenue"] - prior["revenue"]
    result = {"total": total}
    log_total = math.log(current["revenue"] / prior["revenue"])
    for f in FACTORS:
        if log_total == 0:
            result[f] = 0.0
        else:
            result[f] = total * math.log(current[f] / prior[f]) / log_total
    return result


def main_driver(effects):
    """Return the factor name (visitors, conversion or aov) with the largest absolute effect."""
    return max(FACTORS, key=lambda f: abs(effects[f]))


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
        print("%-12s revenue change %9.2f  conversion %.4f -> %.4f  driver: %s" % (
            ch, e["total"], p["conversion"], c["conversion"], main_driver(e)))
