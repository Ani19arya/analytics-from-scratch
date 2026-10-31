"""Build the synthetic sales and access tables for this lesson.

Run from the lesson folder: python3 make_data.py
Writes two files to data/:
  sales.csv        one row per order, September and October 2026, with the
                   city of the kitchen. A few orders came through a partner
                   channel with no city yet, so their city is blank.
  user_access.csv  the security mapping table: one row per (user, city) a
                   user may see. city '*' means every city, including orders
                   with no city. active is 0 for people who have left. It is
                   typed by hand, so it has the usual mess: emails in mixed
                   case or with spaces, and one pair entered twice.
The data is synthetic and deterministic (fixed seed). Emails use the
reserved example.com domain.

The test calls build(seed=...) with another seed to get a second,
different dataset in memory, so a query that hard-codes the answers fails.
"""
import csv
import datetime
import os
import random

DEFAULT_SEED = 411

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CITIES = ["Mumbai", "Nagpur", "Nashik", "Pune"]
FIRST, LAST = datetime.date(2026, 9, 1), datetime.date(2026, 10, 31)


def build(seed=DEFAULT_SEED):
    """Return {"sales": [...], "user_access": [...]} with values as they appear in the CSV files."""
    rng = random.Random(seed)
    sales = []
    day = FIRST
    while day <= LAST:
        for _ in range(rng.randint(5, 11)):
            city = "" if rng.random() < 0.04 else rng.choice(CITIES + ["Mumbai", "Pune"])
            sales.append({"order_date": day.isoformat(), "city": city,
                          "amount": "%.2f" % rng.uniform(120, 900)})
        day += datetime.timedelta(days=1)
    for i, s in enumerate(sales):
        s["order_id"] = "T%05d" % (i + 1)
    sales = [{k: s[k] for k in ("order_id", "order_date", "city", "amount")} for s in sales]

    people = ["asha", "bilal", "chitra", "dev", "esha", "farhan", "gauri"]
    rng.shuffle(people)
    head, m = people[0], people[1:]
    cities = CITIES[:]
    rng.shuffle(cities)
    email = "%s@tiffinbell.example.com"
    access = [
        {"user_email": email % head, "city": "*", "active": 1},           # head office: everything
        {"user_email": email % m[0], "city": cities[0], "active": 1},
        {"user_email": email % m[1], "city": cities[1], "active": 1},
        {"user_email": email % m[1], "city": cities[0], "active": 1},     # covers two cities
        {"user_email": email % m[1], "city": cities[1], "active": 1},     # the same pair typed twice
        {"user_email": email % m[2], "city": cities[2], "active": 0},     # left; nobody else has this city
        {"user_email": email % m[3], "city": cities[3], "active": 1},
        # an analyst typed with capitals and a trailing space
        {"user_email": " " + (email % m[4]).capitalize().replace("@t", "@T") + " ", "city": cities[3], "active": 1},
    ]
    rng.shuffle(access)
    return {"sales": sales, "user_access": access}


def main():
    os.makedirs(DATA, exist_ok=True)
    for name, rows in build().items():
        with open(os.path.join(DATA, name + ".csv"), "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print("wrote %d rows to data/%s.csv" % (len(rows), name))


if __name__ == "__main__":
    main()
