"""Build the data for capstone 10-02: Chordwhistle retention and cohorts.

Chordwhistle is a fictional guitar learning app (iOS and Android) with short
lessons. The data is synthetic and deterministic (fixed seed). It is the raw
export the analyst receives on 5 October 2026, mess included:

data/users.csv     one row per load of a sign-up: user_id, signup_date,
                   platform, source, account_type.
data/activity.csv  one row per user and month the app reported: user_id,
                   activity_month, lessons_completed, loaded_at.

The mess planted in it:
- Duplicates: some users and some user-months are loaded twice.
- Staff accounts (account_type "staff") that use the app every month.
- Late rows: October 2026 is in progress. Its rows hold the first days only
  and more will arrive, so October is not a complete month.
- A definition change halfway: until May 2026 the activity job wrote a row
  for every user who OPENED the app in a month, even with 0 lessons. From
  June 2026 it writes rows only for users who completed at least 1 lesson.
  "Any row" therefore means something different before and after June;
  "lessons_completed >= 1" means the same thing in every month.

The story in it: a paid social campaign in April and May brought big
cohorts of users who stop after their first month far more often than
organic or referral users. Within each source, retention is the same in
every cohort.

    python3 make_data.py                          writes both CSVs (seed 2002)
    import make_data; make_data.build(seed=9)     returns the rows for another seed
"""
import csv
import datetime
import os
import random

SEED = 2002
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
MONTHS = ["2026-%02d" % m for m in range(1, 11)]  # January to October 2026
SIGNUP_MONTHS = MONTHS[:8]  # January to August
DEFINITION_CHANGE = "2026-06"
EXPORT = "2026-10-05"
# mean sign-ups per month, by source
NEW_USERS = {"organic": [40] * 8, "referral": [12] * 8,
             "paid_social": [8, 8, 8, 110, 50, 8, 8, 8]}
# chance of being engaged in month 1 (given engaged in month 0), and in later months (given engaged before)
KEEP = {"organic": (0.55, 0.82), "referral": (0.60, 0.84), "paid_social": (0.12, 0.70)}
COMEBACK = 0.06
USER_FIELDS = ["user_id", "signup_date", "platform", "source", "account_type"]
ACTIVITY_FIELDS = ["user_id", "activity_month", "lessons_completed", "loaded_at"]


def month_after(month, k=1):
    y, m = int(month[:4]), int(month[5:7]) + k
    while m > 12:
        y, m = y + 1, m - 12
    return "%d-%02d" % (y, m)


def poisson(rng, lam):
    limit, k, p = pow(2.718281828459045, -lam), 0, 1.0
    while True:
        p *= rng.random()
        if p < limit:
            return k
        k += 1


def build(seed=SEED):
    """Return {"users": [...], "activity": [...]}, each row a dict of text values."""
    rng = random.Random(seed)
    users, activity = [], []

    def add_user(month, source, account_type):
        uid = "U%05d" % (len(users) + 1)
        day = rng.randint(1, 28)
        users.append({"user_id": uid, "signup_date": "%s-%02d" % (month, day),
                      "platform": "android" if rng.random() < 0.55 else "ios", "source": source,
                      "account_type": account_type})
        return uid

    def add_row(uid, month, lessons):
        if month == "2026-10":
            loaded = EXPORT
        else:
            loaded = month_after(month) + "-%02d" % rng.choice([1, 1, 1, 2])
        row = {"user_id": uid, "activity_month": month, "lessons_completed": str(lessons), "loaded_at": loaded}
        activity.append(row)
        if rng.random() < 0.03:
            activity.append(dict(row))

    for i, month in enumerate(SIGNUP_MONTHS):
        for source in ("organic", "referral", "paid_social"):
            for _ in range(poisson(rng, NEW_USERS[source][i])):
                uid = add_user(month, source, "customer")
                keep1, keep = KEEP[source]
                engaged, last_seen = rng.random() < 0.85, 0
                for k, m in enumerate(MONTHS[i:]):
                    if k > 0:
                        p = (keep1 if k == 1 else keep) if engaged else COMEBACK
                        engaged = rng.random() < p
                    if m == "2026-10" and rng.random() < 0.7:
                        continue  # most of October has not happened yet
                    if engaged:
                        last_seen = k
                        add_row(uid, m, 1 + poisson(rng, 3))
                    elif m < DEFINITION_CHANGE and k - last_seen <= 2 and rng.random() < 0.45:
                        add_row(uid, m, 0)  # opened the app, no lesson: only logged before June
    for _ in range(5):
        uid = add_user(rng.choice(SIGNUP_MONTHS[:2]), "organic", "staff")
        signup_month = users[-1]["signup_date"][:7]
        for m in MONTHS[MONTHS.index(signup_month):]:
            add_row(uid, m, 2 + poisson(rng, 6))

    out_users = []
    for u in users:
        out_users.append(u)
        if rng.random() < 0.02:
            out_users.append(dict(u))
    rng.shuffle(out_users)
    activity.sort(key=lambda r: (r["loaded_at"], r["user_id"], r["activity_month"]))
    return {"users": out_users, "activity": activity}


def write_csv(rows, fields, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_all(data, folder):
    write_csv(data["users"], USER_FIELDS, os.path.join(folder, "users.csv"))
    write_csv(data["activity"], ACTIVITY_FIELDS, os.path.join(folder, "activity.csv"))


def main():
    data = build()
    write_all(data, DATA)
    print("wrote", len(data["users"]), "user rows and", len(data["activity"]), "activity rows to", DATA)


if __name__ == "__main__":
    main()
