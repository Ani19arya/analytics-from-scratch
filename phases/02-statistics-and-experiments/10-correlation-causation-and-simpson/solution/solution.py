"""Lesson 10: correlation by hand, and Simpson's paradox. Worked solution.

Uses only csv and math. Run from the lesson folder:
    python3 solution/solution.py
"""
import csv
import math
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TENURES = ("new", "regular", "veteran")


def read_users(path):
    """Return a list of {"tenure", "notifications", "workouts"} with whole numbers.
    Users with a blank workouts_28d turned tracking off: skip them."""
    users = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if row["workouts_28d"].strip() == "":
                continue
            users.append({"tenure": row["tenure"],
                          "notifications": int(row["notifications_28d"]),
                          "workouts": int(row["workouts_28d"])})
    return users


def mean(values):
    if not values:
        raise ValueError("mean of an empty list")
    return sum(values) / len(values)


def pearson_r(xs, ys):
    """Pearson correlation: sum of products of deviations over the square root of
    the product of the sums of squared deviations."""
    if len(xs) != len(ys):
        raise ValueError("xs and ys must have the same length")
    if len(xs) < 2:
        raise ValueError("need at least 2 pairs")
    mx, my = mean(xs), mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        raise ValueError("r is undefined when one variable does not vary")
    return sxy / math.sqrt(sxx * syy)


def r_by_group(users):
    """{tenure: {"n": users, "r": r or None}} for every tenure present, sorted by name.
    r is None when the group has fewer than 2 users or a variable does not vary."""
    groups = {}
    for u in users:
        groups.setdefault(u["tenure"], []).append(u)
    out = {}
    for tenure in sorted(groups):
        members = groups[tenure]
        try:
            r = pearson_r([u["notifications"] for u in members], [u["workouts"] for u in members])
        except ValueError:
            r = None
        out[tenure] = {"n": len(members), "r": r}
    return out


def within_group_r(users):
    """Correlation after subtracting each tenure group's own means from x and y,
    so only the variation INSIDE each group is left."""
    groups = {}
    for u in users:
        groups.setdefault(u["tenure"], []).append(u)
    dx, dy = [], []
    for members in groups.values():
        mx = mean([u["notifications"] for u in members])
        my = mean([u["workouts"] for u in members])
        for u in members:
            dx.append(u["notifications"] - mx)
            dy.append(u["workouts"] - my)
    return pearson_r(dx, dy)


def is_simpson(overall_r, group_rs):
    """True if every group r that is not None has the opposite sign to overall_r
    (zeros never count as a sign). Needs at least one group r."""
    rs = [r for r in group_rs if r is not None]
    if not rs or overall_r == 0:
        return False
    if overall_r > 0:
        return all(r < 0 for r in rs)
    return all(r > 0 for r in rs)


def summarise(path):
    users = read_users(path)
    overall = pearson_r([u["notifications"] for u in users], [u["workouts"] for u in users])
    groups = r_by_group(users)
    return {
        "n": len(users),
        "overall_r": round(overall, 4),
        "by_tenure": {t: {"n": g["n"], "r": None if g["r"] is None else round(g["r"], 4)}
                      for t, g in groups.items()},
        "within_r": round(within_group_r(users), 4),
        "simpson": is_simpson(overall, [g["r"] for g in groups.values()]),
    }


if __name__ == "__main__":
    for key, value in summarise(os.path.join(HERE, "data", "users.csv")).items():
        print(key, value)
