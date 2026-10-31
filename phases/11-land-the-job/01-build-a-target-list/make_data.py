"""Build data/postings.csv: about 700 SYNTHETIC analyst postings from fictional companies.

Why synthetic: the real Real Analyst Jobs data drop in data/job-market/2026-10 counts postings
by country, by skill and by experience level. It has no company or job rows, so it can tell
you WHERE the roles are but not WHICH companies to put on a list. This file is a stand-in for
postings you save yourself. Every company name, title, date and skill list in it is invented
by this script with a fixed seed. Its numbers say nothing about the real market.

Some rows are planted to teach the traps:
- one very large company (Brackenly Retail) posts many roles, mostly senior and in the US;
- reposter rows copy a careers-page posting a few weeks later, so the same role appears twice
  with a fresher date;
- some postings list no skills at all.

Run: python3 make_data.py
"""
import csv
import datetime
import os
import random

DEFAULT_SEED = 1101
AS_OF = datetime.date(2026, 10, 31)

STEMS = ["Ambergate", "Brackenly", "Cindervale", "Dovecrest", "Elmswick", "Fernhallow", "Glenmarrow",
         "Harrowfield", "Ivelstone", "Juniperhay", "Kestrelwood", "Larkspire", "Marrowby", "Nettlecombe",
         "Quillary", "Rookmere", "Saltbrae", "Thistlemoor", "Umberlane", "Vantorre", "Wrenhaven",
         "Yarrowick", "Zelvane", "Corrowen", "Brisketon", "Tallowmere", "Pellinor", "Ostravel",
         "Mirefield", "Hollowmint"]
SECTORS = ["Retail", "Insurance", "Logistics", "Health", "Foods", "Energy", "Travel", "Telecom",
           "Lending", "Games"]
GIANT = "Brackenly Retail"

COUNTRIES = ["GB", "IE", "US", "IN", "DE", "NL"]
HOME_WEIGHTS = [0.40, 0.12, 0.18, 0.15, 0.08, 0.07]
LEVELS = ["Entry Level", "Mid Level", "Senior", "Lead / Staff", "Not Specified"]
LEVEL_WEIGHTS = [0.14, 0.30, 0.10, 0.08, 0.38]
GIANT_LEVEL_WEIGHTS = [0.03, 0.12, 0.45, 0.30, 0.10]
SKILLS = ["SQL", "Python", "Excel", "Tableau", "Power BI", "Looker", "R", "dbt", "Jira", "Snowflake", "SAS"]
SKILL_CHANCE = {"SQL": 0.70, "Python": 0.45, "Excel": 0.45, "Tableau": 0.30, "Power BI": 0.30,
                "Looker": 0.10, "R": 0.14, "dbt": 0.08, "Jira": 0.10, "Snowflake": 0.10, "SAS": 0.06}
GIANT_SKILL_CHANCE = {"SQL": 0.85, "Python": 0.70, "Excel": 0.30, "Tableau": 0.40, "Power BI": 0.05,
                      "Looker": 0.10, "R": 0.30, "dbt": 0.25, "Jira": 0.10, "Snowflake": 0.40, "SAS": 0.10}
TITLES = ["Data Analyst", "Business Analyst", "Reporting Analyst", "BI Analyst", "Product Analyst",
          "Operations Analyst", "Financial Analyst", "Marketing Analyst", "Insights Analyst",
          "Commercial Analyst", "Pricing Analyst", "Supply Chain Analyst"]
CASE_VARIANTS = {"SQL": ["SQL", "sql"], "Power BI": ["Power BI", "power bi"], "Excel": ["Excel", "excel"]}


def company_names():
    names = []
    for i, stem in enumerate(STEMS):
        for j in range(4):
            names.append("%s %s" % (stem, SECTORS[(i * 3 + j * 7) % len(SECTORS)]))
    if GIANT not in names:
        names[4] = GIANT
    return names


def pick(options, weights, rng):
    r, total = rng.random(), 0.0
    for option, w in zip(options, weights):
        total += w
        if r < total:
            return option
    return options[-1]


def make_posting(rng, company, country, giant):
    level = pick(LEVELS, GIANT_LEVEL_WEIGHTS if giant else LEVEL_WEIGHTS, rng)
    chance = GIANT_SKILL_CHANCE if giant else SKILL_CHANCE
    skills = []
    if rng.random() >= 0.10:
        skills = [rng.choice(CASE_VARIANTS.get(s, [s])) for s in SKILLS if rng.random() < chance[s]]
        rng.shuffle(skills)
    title = rng.choice(TITLES)
    if level == "Senior":
        title = "Senior " + title
    elif level == "Lead / Staff":
        title = "Lead " + title
    age = rng.randint(0, 75)
    return {"company": company, "title": title, "country": country, "seniority": level,
            "skills": ", ".join(skills), "posted_date": (AS_OF - datetime.timedelta(days=age)).isoformat(),
            "source": "careers_page"}


def build(seed=DEFAULT_SEED):
    """Return the list of posting dicts for this seed. Nothing is written."""
    rng = random.Random(seed)
    rows = []
    for company in company_names():
        giant = company == GIANT
        home = pick(COUNTRIES, HOME_WEIGHTS, rng)
        n = 60 if giant else rng.choice([1, 2, 2, 3, 3, 4, 5, 6, 8, 10])
        for _ in range(n):
            if giant:
                country = pick(["US", "GB", "IN", "DE"], [0.6, 0.15, 0.2, 0.05], rng)
            else:
                country = home if rng.random() < 0.75 else rng.choice(COUNTRIES)
            rows.append(make_posting(rng, company, country, giant))
    reposts = []
    for r in rows:
        if r["source"] == "careers_page" and rng.random() < 0.08:
            first = datetime.date.fromisoformat(r["posted_date"])
            later = min(AS_OF, first + datetime.timedelta(days=rng.randint(10, 40)))
            reposts.append(dict(r, posted_date=later.isoformat(), source="reposter",
                                title=r["title"].upper() if rng.random() < 0.3 else r["title"] + " "))
    rows.extend(reposts)
    rng.shuffle(rows)
    for i, r in enumerate(rows, 1):
        r["posting_id"] = "J%04d" % i
    return rows


FIELDS = ["posting_id", "company", "title", "country", "seniority", "skills", "posted_date", "source"]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    rows = build()
    with open(os.path.join(data, "postings.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print("wrote %d synthetic postings to %s" % (len(rows), os.path.join(data, "postings.csv")))


if __name__ == "__main__":
    main()
