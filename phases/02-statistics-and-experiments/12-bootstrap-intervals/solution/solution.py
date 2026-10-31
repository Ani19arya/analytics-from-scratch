"""Lesson 12: percentile bootstrap intervals for a median and a ratio of sums.
Worked solution. Uses only csv and random. Run from the lesson folder:
    python3 solution/solution.py
"""
import csv
import os
import random

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_orders(path):
    """Order values in file order. A blank value is not confirmed yet: skip it."""
    values = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if row["order_value"].strip():
                values.append(float(row["order_value"]))
    return values


def read_sessions(path):
    """Return (per_session, per_user).
    per_session: one (1, revenue) pair per session, in file order.
    per_user:    one (sessions, total revenue) pair per user, sorted by user_id."""
    per_session = []
    users = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            revenue = float(row["revenue"])
            per_session.append((1, revenue))
            cell = users.setdefault(int(row["user_id"]), [0, 0.0])
            cell[0] += 1
            cell[1] += revenue
    per_user = [(users[u][0], users[u][1]) for u in sorted(users)]
    return per_session, per_user


def median(values):
    if not values:
        raise ValueError("median of an empty list")
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def ratio_of_sums(pairs):
    """sum of the second items / sum of the first items: total revenue / total sessions."""
    denominator = sum(p[0] for p in pairs)
    if denominator == 0:
        raise ValueError("the denominator adds up to 0")
    return sum(p[1] for p in pairs) / denominator


def bootstrap(units, statistic, n_boot=2000, seed=0):
    """Resample the units with replacement n_boot times, same size as the data,
    and return the statistic of each resample."""
    if not units:
        raise ValueError("nothing to resample")
    if n_boot < 1:
        raise ValueError("n_boot must be at least 1")
    rng = random.Random(seed)
    k = len(units)
    return [statistic(rng.choices(units, k=k)) for _ in range(n_boot)]


def percentile(values, q):
    """The q-th quantile (0 <= q <= 1) with linear interpolation between the
    two nearest sorted values, at position q * (n - 1)."""
    if not values:
        raise ValueError("percentile of an empty list")
    if not 0 <= q <= 1:
        raise ValueError("q must be between 0 and 1")
    s = sorted(values)
    pos = q * (len(s) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def percentile_interval(stats, level=0.95):
    if not 0 < level < 1:
        raise ValueError("level must be between 0 and 1")
    tail = (1 - level) / 2
    return (percentile(stats, tail), percentile(stats, 1 - tail))


def summarise(orders_path, sessions_path, n_boot=2000, seed=0):
    orders = read_orders(orders_path)
    per_session, per_user = read_sessions(sessions_path)
    med_low, med_high = percentile_interval(bootstrap(orders, median, n_boot, seed))
    user_low, user_high = percentile_interval(bootstrap(per_user, ratio_of_sums, n_boot, seed))
    sess_low, sess_high = percentile_interval(bootstrap(per_session, ratio_of_sums, n_boot, seed))
    return {
        "n_orders": len(orders),
        "median": round(median(orders), 2),
        "median_ci": (round(med_low, 2), round(med_high, 2)),
        "n_users": len(per_user),
        "n_sessions": len(per_session),
        "revenue_per_session": round(ratio_of_sums(per_user), 2),
        "ratio_ci_users": (round(user_low, 2), round(user_high, 2)),
        "ratio_ci_sessions": (round(sess_low, 2), round(sess_high, 2)),
    }


if __name__ == "__main__":
    s = summarise(os.path.join(HERE, "data", "orders.csv"), os.path.join(HERE, "data", "sessions.csv"))
    for key, value in s.items():
        print(key, value)
