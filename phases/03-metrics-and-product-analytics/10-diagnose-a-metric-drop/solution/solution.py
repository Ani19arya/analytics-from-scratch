"""Lesson 10: diagnose a metric drop. Worked answer.

The order of questions:
1. Is the drop real in the data? Compare with the same weekday a week earlier.
2. Did an independent source (server_users, from the backend) fall too?
   If not, the users are still there and the measurement broke.
3. Where is it? Split the change by each dimension and see which slice holds it.
4. Confirm: tracking coverage (dau / server_users) per platform and version.
5. Size it: what DAU would have been with normal coverage.
"""
import csv

DROP_THRESHOLD = -0.05   # a fall of more than 5% is worth diagnosing


def load(path):
    """Return the rows as dicts, with server_users and dau as ints."""
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            row["server_users"] = int(row["server_users"])
            row["dau"] = int(row["dau"])
            rows.append(row)
    return rows


def totals(rows, date, dims=()):
    """{key: [dau, server_users]} for one date, where key is the tuple of the
    values of dims (an empty tuple when dims is empty)."""
    out = {}
    for row in rows:
        if row["date"] != date:
            continue
        key = tuple(row[d] for d in dims)
        cell = out.setdefault(key, [0, 0])
        cell[0] += row["dau"]
        cell[1] += row["server_users"]
    return out


def pct_change(old, new):
    """(new - old) / old, or None when old is 0."""
    if old == 0:
        return None
    return (new - old) / old


def contributions(rows, dim, base_date, date):
    """How much of the DAU change from base_date to date each value of dim holds.
    Return a list of (value, base_dau, dau, change, share_of_change), biggest fall first
    (ties by value). share_of_change is change / total change, or None if the total did not move."""
    base = totals(rows, base_date, (dim,))
    now = totals(rows, date, (dim,))
    total_change = sum(v[0] for v in now.values()) - sum(v[0] for v in base.values())
    out = []
    for key in set(base) | set(now):
        b = base.get(key, [0, 0])[0]
        n = now.get(key, [0, 0])[0]
        change = n - b
        share = change / total_change if total_change else None
        out.append((key[0], b, n, change, share))
    out.sort(key=lambda t: (t[3], t[0]))
    return out


def coverage(rows, date, dims):
    """{key: dau / server_users} for one date, or None for a key with no server users."""
    return {k: (v[0] / v[1] if v[1] else None) for k, v in totals(rows, date, dims).items()}


def diagnose(rows, base_date, date):
    """Return {"dau_change", "server_change", "verdict", "suspect"}.
    verdict: "no drop" if DAU did not fall by more than 5% (or cannot be compared);
             "real" if server_users fell by at least half as much as DAU (in relative terms);
             "tracking" otherwise.
    suspect: for "tracking", the (platform, app_version) with the lowest coverage on date
             (ties by key); otherwise None."""
    b = totals(rows, base_date).get((), [0, 0])
    n = totals(rows, date).get((), [0, 0])
    dau_change = pct_change(b[0], n[0])
    server_change = pct_change(b[1], n[1])
    result = {"dau_change": dau_change, "server_change": server_change, "verdict": "no drop", "suspect": None}
    if dau_change is None or dau_change >= DROP_THRESHOLD:
        return result
    if server_change is not None and server_change <= dau_change / 2:
        result["verdict"] = "real"
        return result
    result["verdict"] = "tracking"
    cov = coverage(rows, date, ("platform", "app_version"))
    ranked = sorted((c, k) for k, c in cov.items() if c is not None)
    result["suspect"] = ranked[0][1] if ranked else None
    return result


def corrected_dau(rows, date, suspect):
    """DAU on date if the suspect (platform, app_version) had normal tracking: its
    server_users times the coverage of every other segment that day, rounded."""
    cells = totals(rows, date, ("platform", "app_version"))
    others = [v for k, v in cells.items() if k != suspect]
    other_dau = sum(v[0] for v in others)
    other_server = sum(v[1] for v in others)
    if suspect not in cells:
        return other_dau
    normal = other_dau / other_server if other_server else 0.0
    return int(round(other_dau + cells[suspect][1] * normal))


if __name__ == "__main__":
    import os
    data = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "daily_users.csv")
    rows = load(data)
    base, day = "2026-10-15", "2026-10-22"
    d = diagnose(rows, base, day)
    print("DAU change %+.1f%%   server users change %+.1f%%   verdict: %s   suspect: %s" % (
        100 * d["dau_change"], 100 * d["server_change"], d["verdict"], d["suspect"]))
    for dim in ("platform", "city"):
        for value, b, n, change, share in contributions(rows, dim, base, day):
            print("  %-8s %-8s %5d -> %5d  change %+5d  share of change %s" % (
                dim, value, b, n, change, "-" if share is None else "%.0f%%" % (100 * share)))
    for key, c in sorted(coverage(rows, day, ("platform", "app_version")).items()):
        print("  coverage %-8s %-4s %.3f" % (key[0], key[1], c))
    fixed = corrected_dau(rows, day, d["suspect"])
    base_dau = totals(rows, base)[()][0]
    print("corrected DAU %d vs %d a week earlier (%+.1f%%)" % (fixed, base_dau, 100 * pct_change(base_dau, fixed)))
