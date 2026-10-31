"""Build the synthetic CRM contacts and the app's signup counts for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/crm_contacts.csv and data/app_signups.csv.
The data is synthetic and deterministic (fixed seed). Email addresses use the
reserved .example domains, so none of them can belong to a real person.

The story built into the data: Tallyo's app has one account per person. The
CRM got a nightly copy of every account (source app_sync), and on 2 October
2026 someone also imported the old marketing tool's contact list (source
import_mkt). That import copied about a third of the people who had signed up
by then, and the copies are not always exact:
  - some are exact copies, down to updated_at,
  - some have the email in capitals,
  - some have spaces around the email,
  - some have a "+tag" the marketing forms added (asha+webinar@...).
Each row has its own updated_at, and the newest row holds the current plan.
A few people signed up with a phone number and have no email at all. They are
real, separate customers, and the marketing tool never had them, so they have
no copies. contact_id is a random CRM id, so its order says
nothing about which row is older.

build(seed) returns the rows without writing anything. The test calls it with
a second seed to check your queries on data you have not seen.
"""
import csv
import datetime
import os
import random

SEED = 808
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIRST = ["asha", "bilal", "chen", "divya", "elena", "farid", "gita", "hugo", "isha", "jonas", "kavya", "leo",
         "maya", "nikhil", "omar", "priya", "quinn", "ravi", "sara", "tomas", "uma", "vikram", "wen", "zara"]
LAST = ["rao", "khan", "patel", "silva", "mehta", "nair", "iyer", "das", "shah", "roy", "jain", "bose"]
DOMAINS = ["mailbox.example", "post.example", "inbox.example", "letters.example"]
PLANS = ["free", "plus", "family"]
TAGS = ["webinar", "promo", "news"]
START = datetime.date(2026, 8, 1)
IMPORT_DAY = datetime.date(2026, 10, 2)
LAST_DAY = datetime.date(2026, 10, 31)


def stamp(rng, first_day, last_day):
    day = first_day + datetime.timedelta(days=rng.randint(0, (last_day - first_day).days))
    return "%s %02d:%02d:%02d" % (day.isoformat(), rng.randint(0, 23), rng.randint(0, 59), rng.randint(0, 59))


def build(seed=SEED):
    """Return {"crm_contacts": [...], "app_signups": [...]}, rows as dicts."""
    rng = random.Random(seed)
    people, used = [], set()
    n_people = rng.randint(400, 440)
    while len(people) < n_people:
        first, last = rng.choice(FIRST), rng.choice(LAST)
        local = "%s.%s%d" % (first, last, rng.randint(1, 99))
        email = "%s@%s" % (local, rng.choice(DOMAINS))
        if email in used:
            continue
        used.add(email)
        signup = START + datetime.timedelta(days=rng.randint(0, (LAST_DAY - START).days))
        people.append({"email": None if rng.random() < 0.04 else email,
                       "name": "%s %s" % (first.title(), last.title()), "signup": signup})
    rows = []
    for p in people:
        current = rng.choice(PLANS)
        original = {"email": p["email"], "full_name": p["name"], "signup_date": p["signup"].isoformat(),
                    "plan": current, "updated_at": stamp(rng, p["signup"], LAST_DAY), "source": "app_sync"}
        rows.append(original)
        if p["email"] is None or p["signup"] >= IMPORT_DAY or rng.random() > 0.35:
            continue                              # the marketing tool only knew people by email
        copy = dict(original, source="import_mkt")
        kind = rng.random()
        if kind < 0.35:
            pass                                  # an exact copy, updated_at included
        else:
            local, domain = p["email"].split("@")
            if kind < 0.55:
                copy["email"] = p["email"].upper()
            elif kind < 0.75:
                copy["email"] = "  %s " % p["email"]
            else:
                copy["email"] = "%s+%s@%s" % (local, rng.choice(TAGS), domain)
            copy["updated_at"] = stamp(rng, p["signup"], LAST_DAY)
            if copy["updated_at"] == original["updated_at"]:
                copy["updated_at"] = original["updated_at"][:-2] + "%02d" % ((int(original["updated_at"][-2:]) + 1) % 60)
            older = copy if copy["updated_at"] < original["updated_at"] else original
            older["plan"] = rng.choice(PLANS)     # the older row may hold a stale plan
            newer = original if older is copy else copy
            newer["plan"] = current
        rows.append(copy)
    ids = rng.sample(range(10000, 99999), len(rows))
    for r, i in zip(rows, ids):
        r["contact_id"] = "C%05d" % i
    rows.sort(key=lambda r: (r["updated_at"], r["contact_id"]))
    contacts = [{"contact_id": r["contact_id"], "email": r["email"], "full_name": r["full_name"],
                 "signup_date": r["signup_date"], "plan": r["plan"], "updated_at": r["updated_at"],
                 "source": r["source"]} for r in rows]
    months = {}
    for p in people:
        key = p["signup"].strftime("%Y-%m")
        months[key] = months.get(key, 0) + 1
    app = [{"month": m, "signups": n} for m, n in sorted(months.items())]
    return {"crm_contacts": contacts, "app_signups": app}


def write(name, rows):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/%s" % (len(rows), name))


def main():
    os.makedirs(DATA, exist_ok=True)
    tables = build()
    write("crm_contacts.csv", tables["crm_contacts"])
    write("app_signups.csv", tables["app_signups"])


if __name__ == "__main__":
    main()
