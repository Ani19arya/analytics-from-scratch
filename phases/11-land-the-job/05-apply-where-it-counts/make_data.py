"""Build data/postings.csv: 40 SYNTHETIC analyst postings that one job seeker saved this week,
data/profile.json: that job seeker's SYNTHETIC skills profile and weekly time budget, and
data/labels.csv: the red flag the generator planted in each posting (blank for none).

Every company, title, date, salary and note here is invented by this script. The company
names are fictional (several are reused from other lessons in this course), and "Relistly"
is a fictional reposting site. The red flags planted below (a fee to apply, unpaid trial
work, an "Entry Level" label on a senior job, a reposted listing) are the patterns the lesson
teaches you to catch; how often they appear here is made up, not a market rate.

The real numbers this lesson quotes are in data/real_snapshot_2026-10-31.json, which this
script does not touch.

Run: python3 make_data.py
"""
import csv
import datetime
import json
import os
import random

DEFAULT_SEED = 1105
N_POSTINGS = 40
AS_OF = datetime.date(2026, 10, 31)

COMPANIES = ["Tiffinbell", "Larkspur Coffee", "Fitloop", "Kestrel Home", "Harbor Mealkits",
             "Tidewater Outdoor", "Brightloom", "Fernhill Software", "Wrenloom", "Tallyfern",
             "Ledgerlark", "Copperwren Grocery", "Bramblequay Bikes", "Parcelwick", "Pantrywren",
             "Kettlemoor", "Brackenbee", "Learnhaven", "Larkspur Goods", "Northwind Desk"]

PLAIN_TITLES = ["Data Analyst", "Junior Data Analyst", "Business Analyst", "Reporting Analyst",
                "Marketing Analyst", "Operations Analyst", "Product Analyst", "BI Analyst",
                "Data Analyst I", "Associate Analyst, Insights"]
SENIOR_TITLES = ["Senior Manager, Analytics", "Senior Data Analyst", "Lead Business Analyst",
                 "Analytics Manager", "Principal Analyst"]

SKILL_POOL = ["SQL", "Excel", "Tableau", "Power BI", "Python", "R", "Looker", "dbt",
              "statistics", "A/B testing"]
COMMON_MUST = ["SQL", "Excel", "SQL", "SQL", "Python", "Tableau", "Power BI"]

NORMAL_NOTES = ["Hybrid, 3 days a week in the office.",
                "Interview includes a 45-minute SQL exercise.",
                "Fully on-site.",
                "We never charge an application fee.",
                "Remote within the country of the posting.",
                "Short take-home task, paid at our contractor rate.",
                "",
                ""]
FEE_NOTES = ["A 30 USD processing fee is due with your application.",
             "Shortlisted candidates pay a registration fee for onboarding."]
UNPAID_NOTES = ["Final stage is an unpaid trial week on live client work.",
                "Candidates complete an unpaid test project of about 20 hours."]

# How many postings get each planted problem. The rest are ordinary postings.
PLANTED = {"fee": 2, "unpaid": 2, "senior_title": 2, "senior_salary": 1, "repost": 5}
HOURS = [0.5, 1.0, 1.0, 1.5, 1.5, 2.0, 2.0, 2.5, 3.0]


def build(seed=DEFAULT_SEED, n=N_POSTINGS):
    """Return {"postings": [...], "profile": {...}} for this seed. Nothing is written."""
    rng = random.Random(seed)
    kinds = []
    for kind, count in PLANTED.items():
        kinds += [kind] * count
    kinds += ["plain"] * (n - len(kinds))
    rng.shuffle(kinds)
    postings, labels = [], []
    for i, kind in enumerate(kinds, 1):
        company = rng.choice(COMPANIES)
        title = rng.choice(SENIOR_TITLES if kind == "senior_title" else PLAIN_TITLES)
        label = rng.choice(["Entry Level", "Entry Level", "Mid Level", "Not Specified"])
        if kind in ("senior_title", "senior_salary"):
            label = "Entry Level"
        source = rng.choice(["careers_page", "careers_page", "job_board"])
        if kind == "repost":
            source = "repost"
            company = company + " (via Relistly)"
        age = rng.choice([0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 19, 24, 33, 41, 58])
        first_seen = (AS_OF - datetime.timedelta(days=age)).isoformat()
        if rng.random() < 0.06:
            first_seen = ""  # the board did not record when it first saw the posting
        if kind == "senior_salary":
            low = rng.choice([128000, 141000, 156000])
        elif rng.random() < 0.55:
            low = rng.choice([52000, 58000, 64000, 70000, 76000, 84000])
        else:
            low = None
        high = None if low is None else low + rng.choice([8000, 12000, 18000, 24000])
        n_must = rng.choice([1, 2, 2, 3, 3])
        must = []
        while len(must) < n_must:
            s = rng.choice(COMMON_MUST if rng.random() < 0.7 else SKILL_POOL)
            if s not in must:
                must.append(s)
        nice = [s for s in rng.sample(SKILL_POOL, rng.choice([0, 1, 2, 3])) if s not in must]
        if kind == "fee":
            note = rng.choice(FEE_NOTES)
        elif kind == "unpaid":
            note = rng.choice(UNPAID_NOTES)
        else:
            note = rng.choice(NORMAL_NOTES)
        # Write some skills in other cases, the way real postings do.
        must = [s.lower() if rng.random() < 0.15 else s for s in must]
        postings.append({
            "posting_id": "J%02d" % i, "company": company, "title": title, "seniority_label": label,
            "source": source, "first_seen": first_seen,
            "salary_min_usd": "" if low is None else str(low), "salary_max_usd": "" if high is None else str(high),
            "must_have": ";".join(must), "nice_to_have": ";".join(nice), "notes": note,
            "est_hours": str(rng.choice(HOURS)),
        })
        truth = {"fee": "fee_to_apply", "unpaid": "unpaid_work", "senior_title": "seniority_mismatch",
                 "senior_salary": "seniority_mismatch", "repost": "repost"}.get(kind, "")
        labels.append({"posting_id": "J%02d" % i, "planted_flag": truth})
    profile = {
        "about": "SYNTHETIC skills profile of a fictional job seeker, built by make_data.py",
        "as_of": AS_OF.isoformat(),
        "target_seniority": "entry",
        "skills": ["SQL", "Excel", "Tableau", "Python", "statistics"],
        "weekly_hours": 10,
        "entry_salary_ceiling_usd": 110000,
    }
    return {"postings": postings, "profile": profile, "labels": labels}


FIELDS = ["posting_id", "company", "title", "seniority_label", "source", "first_seen",
          "salary_min_usd", "salary_max_usd", "must_have", "nice_to_have", "notes", "est_hours"]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    d = build()
    with open(os.path.join(data, "postings.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(d["postings"])
    with open(os.path.join(data, "labels.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["posting_id", "planted_flag"], lineterminator="\n")
        w.writeheader()
        w.writerows(d["labels"])
    with open(os.path.join(data, "profile.json"), "w") as f:
        json.dump(d["profile"], f, indent=2)
        f.write("\n")
    print("wrote", data)


if __name__ == "__main__":
    main()
