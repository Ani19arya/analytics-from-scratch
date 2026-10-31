"""Lesson 08: retention curves and churn. Worked answer.

day offset   = visit_date - signup_date, in days (day 0 is the signup day)
classic N    = share of eligible users who visited ON day N
unbounded N  = share of eligible users who visited on day N OR ANY LATER day
eligible N   = users whose signup_date + N is on or before the as_of date
churned by N = 1 - unbounded N (never seen again from day N on)
"""
import csv
import datetime


def to_date(text):
    return datetime.date(int(text[:4]), int(text[5:7]), int(text[8:10]))


def load(users_path, visits_path):
    """Return (signups, offsets).
    signups: {user_id: signup date as datetime.date}
    offsets: {user_id: set of day offsets with a visit}, one entry per signed-up user.
    Visits dated before signup, and visits by unknown users, are dropped."""
    signups = {}
    with open(users_path, newline="") as f:
        for row in csv.DictReader(f):
            signups[row["user_id"]] = to_date(row["signup_date"])
    offsets = {uid: set() for uid in signups}
    with open(visits_path, newline="") as f:
        for row in csv.DictReader(f):
            uid = row["user_id"]
            if uid not in signups or not row["visit_date"]:
                continue
            d = (to_date(row["visit_date"]) - signups[uid]).days
            if d >= 0:
                offsets[uid].add(d)
    return signups, offsets


def eligible_users(signups, n, as_of):
    """Users old enough to have a day n by as_of."""
    return [u for u, s in signups.items() if (as_of - s).days >= n]


def classic_retention(signups, offsets, n, as_of):
    """(retained, eligible): eligible users with a visit on exactly day n."""
    users = eligible_users(signups, n, as_of)
    return sum(1 for u in users if n in offsets.get(u, ())), len(users)


def unbounded_retention(signups, offsets, n, as_of):
    """(retained, eligible): eligible users with a visit on day n or any later day."""
    users = eligible_users(signups, n, as_of)
    return sum(1 for u in users if any(d >= n for d in offsets.get(u, ()))), len(users)


def rate(pair):
    """retained / eligible, or None when nobody is eligible."""
    retained, eligible = pair
    return retained / eligible if eligible else None


def week_start(day):
    """The Monday on or before a date, as 'YYYY-MM-DD' text."""
    return (day - datetime.timedelta(days=day.weekday())).isoformat()


def cohort_curves(signups, offsets, days, as_of, kind="classic"):
    """{cohort week Monday: {n: rate or None}} for every signup week and every n in days.
    kind is "classic" or "unbounded". A cohort with no user old enough for day n gets None.
    Users in a cohort who are too young for day n are left out of that cell's denominator."""
    fn = classic_retention if kind == "classic" else unbounded_retention
    weeks = {}
    for u, s in signups.items():
        weeks.setdefault(week_start(s), {})[u] = s
    out = {}
    for wk in sorted(weeks):
        out[wk] = {n: rate(fn(weeks[wk], offsets, n, as_of)) for n in days}
    return out


if __name__ == "__main__":
    import os
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    signups, offsets = load(os.path.join(here, "users.csv"), os.path.join(here, "visits.csv"))
    as_of = datetime.date(2026, 10, 31)
    for n in (1, 7, 14, 30):
        c = classic_retention(signups, offsets, n, as_of)
        b = unbounded_retention(signups, offsets, n, as_of)
        print("day %2d  eligible %3d  classic %.3f  unbounded %.3f" % (n, c[1], rate(c), rate(b)))
    print("classic retention by signup week (- = cohort too young)")
    for wk, row in cohort_curves(signups, offsets, (1, 7, 14, 30), as_of).items():
        size = sum(1 for s in signups.values() if week_start(s) == wk)
        print(wk, "%3d users" % size, "  ".join("d%-2d %s" % (n, "  -  " if r is None else "%.2f " % r) for n, r in row.items()))
