"""Build data/activity.csv: one row per session for a synthetic workout app,
January to September 2026.

Columns: user_id, session_date.
The data is synthetic and deterministic (fixed seed). A user can have more than
one session in a month, and a few rows have a blank user_id (logged-out
sessions), so the learner has to clean before counting. In September fewer new
users arrive and a win-back email brings many lapsed users back, which is the
story the lesson finds.

    python3 make_data.py          writes data/activity.csv (seed 23)
    import make_data; make_data.build(seed=5)   returns the rows for another seed
"""
import csv
import datetime
import os
import random

SEED = 23
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "activity.csv")
FIELDS = ["user_id", "session_date"]
MONTHS = ["2026-%02d" % m for m in range(1, 10)]
NEW_USERS = [40, 44, 48, 50, 52, 54, 56, 58, 34]   # first-ever sessions per month
STAY = 0.62                                         # active last month, active again
RETURN = [0.07] * 8 + [0.26]                        # lapsed user comes back (win-back in September)


def month_days(month):
    year, m = int(month[:4]), int(month[5:])
    nxt = datetime.date(year + (m == 12), m % 12 + 1, 1)
    return (nxt - datetime.date(year, m, 1)).days


def build(seed=SEED):
    """Return {"activity": [row, ...]}. Each row is a dict of text values,
    exactly as written to the CSV, sorted by date then user."""
    rng = random.Random(seed)
    users = []        # [user_id, first month index]
    active = {}       # user_id -> set of month indexes
    next_id = 1
    for i, month in enumerate(MONTHS):
        for uid, _first in users:
            if (i - 1) in active[uid]:
                p = STAY
            else:
                p = RETURN[i]
            if rng.random() < p:
                active[uid].add(i)
        for _ in range(NEW_USERS[i] + rng.randint(-3, 3)):
            uid = next_id
            next_id += 1
            users.append((uid, i))
            active[uid] = {i}
    rows = []
    for uid, _first in users:
        for i in sorted(active[uid]):
            n = 1 if rng.random() < 0.55 else 2
            days = sorted(rng.sample(range(1, month_days(MONTHS[i]) + 1), n))
            for d in days:
                rows.append({"user_id": str(uid), "session_date": "%s-%02d" % (MONTHS[i], d)})
    for i in (2, 5, 8):   # logged-out sessions: no user id
        rows.append({"user_id": "", "session_date": "%s-%02d" % (MONTHS[i], 15)})
    rows.sort(key=lambda r: (r["session_date"], int(r["user_id"] or 0)))
    return {"activity": rows}


def write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    rows = build()["activity"]
    write_csv(rows, OUT)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
