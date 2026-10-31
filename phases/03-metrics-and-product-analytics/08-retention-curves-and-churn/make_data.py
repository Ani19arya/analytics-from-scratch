"""Build data/users.csv and data/visits.csv for a synthetic job marketplace:
job seekers who signed up between 3 August and 25 October 2026, and every day
they visited, up to 31 October 2026 (the day the data was pulled).

users.csv:  user_id, signup_date
visits.csv: user_id, visit_date   (at most one row per user per day)

The data is synthetic and deterministic (fixed seed). Each user visits on some days
until they leave for good. Users who signed up on or after 28 September got a
new onboarding flow and stay a little longer. A few visit rows are dated before the user's signup
(a known tracking glitch), which the learner has to drop.

    python3 make_data.py          writes both files (seed 41)
    import make_data; make_data.build(seed=8)   returns the rows for another seed
"""
import csv
import datetime
import os
import random

SEED = 41
HERE = os.path.dirname(os.path.abspath(__file__))
FIRST_SIGNUP = datetime.date(2026, 8, 3)
LAST_SIGNUP = datetime.date(2026, 10, 25)
AS_OF = datetime.date(2026, 10, 31)
ONBOARDING = datetime.date(2026, 9, 28)
VISIT_RATE = 0.33   # chance of a visit on each day while the user is still around
FIELDS = {"users": ["user_id", "signup_date"], "visits": ["user_id", "visit_date"]}


def lifetime(rng, new_flow):
    """How many days a user keeps using the product before leaving for good.
    Some leave on day 0. The new onboarding flow keeps users a little longer."""
    if rng.random() < (0.25 if new_flow else 0.32):
        return 0
    return int(rng.expovariate(1.0 / (26.0 if new_flow else 20.0)))


def build(seed=SEED):
    """Return {"users": [...], "visits": [...]}, each a list of dicts of text values."""
    rng = random.Random(seed)
    users, visits = [], []
    uid = 1000
    day = FIRST_SIGNUP
    while day <= LAST_SIGNUP:
        n = rng.choice((2, 2, 3, 3, 4)) if day.weekday() < 5 else rng.choice((0, 1, 1, 2))
        for _ in range(n):
            uid += 1
            users.append({"user_id": str(uid), "signup_date": day.isoformat()})
            new_flow = day >= ONBOARDING
            last = min((AS_OF - day).days, lifetime(rng, new_flow))
            for d in range(0, last + 1):
                if d == 0 or rng.random() < VISIT_RATE:
                    visits.append({"user_id": str(uid), "visit_date": (day + datetime.timedelta(days=d)).isoformat()})
            if rng.random() < 0.03:
                glitch = day - datetime.timedelta(days=rng.randint(1, 5))
                visits.append({"user_id": str(uid), "visit_date": glitch.isoformat()})
        day += datetime.timedelta(days=1)
    visits.sort(key=lambda r: (r["visit_date"], r["user_id"]))
    return {"users": users, "visits": visits}


def write_csv(rows, path, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_all(tables, folder):
    for name in ("users", "visits"):
        write_csv(tables[name], os.path.join(folder, name + ".csv"), FIELDS[name])


def main():
    tables = build()
    write_all(tables, os.path.join(HERE, "data"))
    print("wrote", len(tables["users"]), "users and", len(tables["visits"]), "visits")


if __name__ == "__main__":
    main()
