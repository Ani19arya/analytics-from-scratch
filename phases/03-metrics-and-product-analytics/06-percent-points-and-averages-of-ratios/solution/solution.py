"""Lesson 06 solution: percent vs points, ratio of sums vs average of ratios."""
import csv


def read_days(path):
    with open(path, newline="") as f:
        return [{"date": r["date"], "visits": int(r["visits"]), "orders": int(r["orders"])}
                for r in csv.DictReader(f)]


def ratio_of_sums(rows):
    """All orders divided by all visits: the share of visits that ended in an order."""
    visits = sum(r["visits"] for r in rows)
    if visits == 0:
        return None
    return sum(r["orders"] for r in rows) / visits


def average_of_ratios(rows):
    """The plain average of each day's rate. Days with no visits have no rate and are skipped."""
    rates = [r["orders"] / r["visits"] for r in rows if r["visits"] > 0]
    if not rates:
        return None
    return sum(rates) / len(rates)


def weighted_average_of_ratios(rows):
    """Each day's rate weighted by its visits. Algebraically the same as ratio_of_sums."""
    days = [r for r in rows if r["visits"] > 0]
    weight = sum(r["visits"] for r in days)
    if weight == 0:
        return None
    return sum(r["orders"] / r["visits"] * r["visits"] for r in days) / weight


def by_month(rows):
    months = {}
    for r in rows:
        months.setdefault(r["date"][:7], []).append(r)
    return months


def point_change(old, new):
    """Difference between two rates (as fractions), in percentage points."""
    return (new - old) * 100


def percent_change(old, new):
    """Relative change, in percent. None when the old value is 0."""
    if old == 0:
        return None
    return (new - old) / old * 100


def describe_change(old, new):
    pct = percent_change(old, new)
    relative = "n/a" if pct is None else "%+.1f%%" % pct
    return "%.2f%% to %.2f%%: %+.2f points (%s)" % (old * 100, new * 100, point_change(old, new), relative)


def summarise(path):
    months = by_month(read_days(path))
    first, second = sorted(months)
    out = {}
    for month in (first, second):
        rows = months[month]
        out[month] = {"visits": sum(r["visits"] for r in rows), "orders": sum(r["orders"] for r in rows),
                      "ratio_of_sums": ratio_of_sums(rows), "average_of_ratios": average_of_ratios(rows)}
    out["change_ratio_of_sums"] = describe_change(out[first]["ratio_of_sums"], out[second]["ratio_of_sums"])
    out["change_average_of_ratios"] = describe_change(out[first]["average_of_ratios"],
                                                      out[second]["average_of_ratios"])
    return out


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    result = summarise(os.path.join(here, "..", "data", "daily.csv"))
    for key, value in result.items():
        if isinstance(value, dict):
            print(key, "visits", value["visits"], "orders", value["orders"],
                  "ratio of sums %.4f" % value["ratio_of_sums"], "average of ratios %.4f" % value["average_of_ratios"])
        else:
            print(key + ":", value)
