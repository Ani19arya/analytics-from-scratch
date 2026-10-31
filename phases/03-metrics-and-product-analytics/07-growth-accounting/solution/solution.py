"""Lesson 07: growth accounting. Worked answer.

MAU this month = MAU last month + new + resurrected - churned
retained = active last month and this month
new = first active month ever is this month
resurrected = active this month, not last month, but active in some earlier month
churned = active last month, not this month
"""
import csv


def load_activity(path):
    """Read the session log and return {user_id: set of 'YYYY-MM' months with a session}.
    Rows with a blank user_id are skipped: they cannot be tied to a person."""
    activity = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            uid = (row["user_id"] or "").strip()
            if not uid:
                continue
            activity.setdefault(uid, set()).add(row["session_date"][:7])
    return activity


def prev_month(month):
    """'2026-01' -> '2025-12', '2026-09' -> '2026-08'."""
    year, m = int(month[:4]), int(month[5:7])
    if m == 1:
        return "%04d-12" % (year - 1)
    return "%04d-%02d" % (year, m - 1)


def month_range(first, last):
    """Every calendar month from first to last inclusive, as 'YYYY-MM' text."""
    out = []
    month = last
    while month >= first:
        out.append(month)
        month = prev_month(month)
    return out[::-1]


def account(activity, month):
    """Growth accounting for one month. Return a dict with keys
    month, mau, prev_mau, new, retained, resurrected, churned."""
    before = prev_month(month)
    row = {"month": month, "mau": 0, "prev_mau": 0, "new": 0, "retained": 0, "resurrected": 0, "churned": 0}
    for months in activity.values():
        now = month in months
        last = before in months
        earlier = any(m < before for m in months)
        if last:
            row["prev_mau"] += 1
        if now:
            row["mau"] += 1
            if last:
                row["retained"] += 1
            elif earlier:
                row["resurrected"] += 1
            else:
                row["new"] += 1
        elif last:
            row["churned"] += 1
    return row


def growth_table(activity):
    """One account() row for every calendar month from the first to the last month
    in the data, gaps included. An empty activity gives an empty list."""
    months = set()
    for ms in activity.values():
        months |= ms
    if not months:
        return []
    return [account(activity, m) for m in month_range(min(months), max(months))]


def quick_ratio(row):
    """(new + resurrected) / churned: users gained per user lost.
    None when nobody churned (the ratio has no finite value)."""
    if row["churned"] == 0:
        return None
    return (row["new"] + row["resurrected"]) / row["churned"]


if __name__ == "__main__":
    import os
    data = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "activity.csv")
    table = growth_table(load_activity(data))
    print("month    prev_mau  new  retained  resurrected  churned  mau  quick_ratio")
    for r in table:
        q = quick_ratio(r)
        print("%s  %8d  %3d  %8d  %11d  %7d  %3d  %s" % (
            r["month"], r["prev_mau"], r["new"], r["retained"], r["resurrected"], r["churned"], r["mau"],
            "-" if q is None else "%.2f" % q))
