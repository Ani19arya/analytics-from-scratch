"""Build the data for capstone 11-08: a 30-day job search plan.

Everything here is SYNTHETIC and deterministic (fixed seed). The companies are
fictional, and the postings and the application log are invented to teach the
method. They say nothing about the real job market. The real numbers this
capstone quotes are in data/real_snapshot_2026-10-31.json, with provenance.

The job seeker is Kavya Menon (fictional), based in Pune, India. Her profile
is in data/profile.json. The plan runs for 30 days from Monday 2 November 2026.

data/postings.csv   postings she saved on Sunday 1 November 2026, one row per
                    posting: posting_id, company, title, city, country,
                    work_mode, remote_regions, posted_date, closes_on, source,
                    tools, description.
data/app_log.csv    her first week of applications (26 October to 1 November
                    2026), one row per logged event: log_id, application_id,
                    posting_id, channel, event, event_date.
data/profile.json   her situation: home country, cities, hours per week,
                    skills, target role families, plan start.

The mess planted in it:
- Postings that are stale (posted more than 30 days before the plan starts)
  or already closed, and some that close during the plan.
- Reposts: the same role (company, title, city) saved twice under two ids.
- Remote postings that only hire from other countries, or do not say where.
- Postings outside India that say, in their own words, that they will not
  sponsor a visa, and others that say nothing either way.
- Red-flag postings (a fee, a "guaranteed job", a chat-app-only contact).
- Titles from several synonym families, so a search for one phrase misses
  most of the roles.
- In the log: rows typed twice, and a renamed stage halfway through the week
  (Kavya switched tracker templates on 29 October: "phone_screen" became
  "screen").

    python3 make_data.py                         writes the files (seed 1109)
    import make_data; make_data.build(seed=7)    returns the rows for another seed
"""
import csv
import datetime
import json
import os
import random

SEED = 1109
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

PLAN_START = datetime.date(2026, 11, 2)
LOG_START = datetime.date(2026, 10, 26)
LOG_END = datetime.date(2026, 11, 1)
RENAME_DAY = datetime.date(2026, 10, 29)

PROFILE = {
    "name": "Kavya Menon",
    "synthetic": True,
    "home_country": "IN",
    "home_regions": ["IN", "APAC", "WORLDWIDE"],
    "onsite_cities": ["Pune", "Bengaluru", "Mumbai"],
    "needs_sponsorship_outside": "IN",
    "hours_per_week": 10,
    "skills": ["SQL", "Excel", "Tableau", "Python"],
    "target_families": ["data", "business", "product", "bi"],
    "plan_start": PLAN_START.isoformat(),
    "plan_days": 30,
    "stale_after_days": 30,
}

POSTING_FIELDS = ["posting_id", "company", "title", "city", "country", "work_mode", "remote_regions",
                  "posted_date", "closes_on", "source", "tools", "description"]
LOG_FIELDS = ["log_id", "application_id", "posting_id", "channel", "event", "event_date"]

COMPANIES = ["Tiffinbell", "Pottlemere", "Lanternway Courses", "Quillfern Logistics", "Brasswick Retail",
             "Mintgrove Health", "Coralhatch Payments", "Saffronlane Foods", "Dewmark Insurance",
             "Ferncastle Media", "Ottervale Telecom", "Pebblequay Travel", "Larkspin Games",
             "Indigoflint Software", "Juniperwell Pharma", "Kettlebrook Energy", "Moonwick Fashion",
             "Nimbletree Learning", "Orchidbay Bank", "Puddlestone Grocers", "Rivetlane Motors",
             "Silkhaven Hotels", "Thistlecart", "Umbergate Freight", "Velvetfinch Studios",
             "Wrenhollow Analytics", "Yarrowpeak Telecom", "Zinnialoop Retail", "Ambersprout Fintech",
             "Bluequarry Mining"]

# title -> family, with how often each title appears. None = not a target analyst role.
TITLES = [
    ("Data Analyst", "data", 6), ("Insights Analyst", "data", 3), ("Reporting Analyst", "data", 3),
    ("Marketing Insights Analyst", "data", 2), ("Analytics Analyst", "data", 1),
    ("Business Analyst", "business", 6), ("Operations Analyst", "business", 3),
    ("Product Analyst", "product", 3), ("Growth Analyst", "product", 2),
    ("Business Intelligence Analyst", "bi", 3), ("BI Analyst", "bi", 2), ("BI Developer", "bi", 1),
    ("Financial Analyst", None, 3), ("Credit Risk Analyst", None, 2), ("Data Engineer", None, 2),
    ("Data Scientist", None, 2), ("Program Manager, Analytics", None, 1),
]
PREFIXES = [("", 6), ("Junior ", 1), ("Senior ", 2), ("Associate ", 1)]
IN_CITIES = [("Pune", 3), ("Bengaluru", 4), ("Mumbai", 3), ("Hyderabad", 2), ("Chennai", 1), ("Gurugram", 2)]
ABROAD = [("US", ["New York", "Seattle", "Austin"]), ("GB", ["London", "Manchester"]),
          ("SG", ["Singapore"]), ("DE", ["Berlin"])]
REMOTE_SCOPES = [("IN", 3), ("APAC", 1), ("WORLDWIDE", 1), ("", 4), ("US", 4), ("GB;IE", 1), ("IN;SG", 1)]
TOOLS = ["SQL", "Excel", "Tableau", "Python", "Power BI", "Looker", "R", "dbt"]
TOOL_WEIGHTS = [8, 5, 4, 5, 4, 2, 1, 1]

BASE_TEXT = ["You will build dashboards and answer questions from the business with data.",
             "Own weekly reporting and work with product and operations teams.",
             "Turn messy data into clear recommendations for leadership.",
             "Analyse funnels, cohorts and campaigns, and present what you find."]
SPONSOR_YES_TEXT = ["Visa sponsorship available for the right candidate.", "We sponsor visas for this role."]
SPONSOR_NO_TEXT = ["No visa sponsorship is offered.", "We are unable to sponsor visas.",
                   "You must have the right to work in this country."]
RED_FLAG_TEXT = ["A refundable Registration Fee applies before onboarding.",
                 "Guaranteed job after you pay for your training.", "Contact us on WhatsApp only.",
                 "A small security deposit is collected at joining."]


def pick(rng, weighted):
    items = [w[:-1] if len(w) > 2 else w[0] for w in weighted]
    return rng.choices(items, weights=[w[-1] for w in weighted], k=1)[0]


def make_posting(rng, pid):
    title, family = pick(rng, TITLES)
    title = pick(rng, PREFIXES) + title
    company = rng.choice(COMPANIES)
    where = rng.random()
    remote_regions = ""
    sponsor = None
    if where < 0.50:
        country, city = "IN", pick(rng, IN_CITIES)
        work_mode = "hybrid" if rng.random() < 0.5 else "onsite"
    elif where < 0.72:
        country, cities = rng.choice(ABROAD)
        city = rng.choice(cities)
        work_mode = "hybrid" if rng.random() < 0.4 else "onsite"
        sponsor = rng.choices(["yes", "no", None], weights=[2, 4, 4])[0]
    else:
        remote_regions = pick(rng, REMOTE_SCOPES)
        home = {"APAC": "SG", "WORLDWIDE": "US", "": rng.choice(["IN", "US", "GB"])}
        country = home.get(remote_regions, remote_regions.split(";")[0])
        city, work_mode = "Remote", "remote"
    age = rng.choices([rng.randint(0, 14), rng.randint(15, 30), rng.randint(31, 75)], weights=[6, 3, 2])[0]
    posted = PLAN_START - datetime.timedelta(days=1 + age)
    closes = ""
    r = rng.random()
    if r < 0.08:
        closes = (PLAN_START - datetime.timedelta(days=rng.randint(1, 6))).isoformat()
    elif r < 0.30:
        closes = (PLAN_START + datetime.timedelta(days=rng.randint(3, 25))).isoformat()
    k = rng.randint(2, 4)
    tools = []
    while len(tools) < k:
        t = rng.choices(TOOLS, weights=TOOL_WEIGHTS)[0]
        if t not in tools:
            tools.append(t)
    text = [rng.choice(BASE_TEXT)]
    if sponsor == "yes":
        text.append(rng.choice(SPONSOR_YES_TEXT))
    elif sponsor == "no":
        text.append(rng.choice(SPONSOR_NO_TEXT))
    elif country != "IN" and work_mode != "remote" and rng.random() < 0.1:
        # a posting that contradicts itself: the "no" wins
        text.append(rng.choice(SPONSOR_YES_TEXT) + " " + rng.choice(SPONSOR_NO_TEXT))
    if rng.random() < 0.07:
        text.append(rng.choice(RED_FLAG_TEXT))
    return {"posting_id": pid, "company": company, "title": title, "city": city, "country": country,
            "work_mode": work_mode, "remote_regions": remote_regions, "posted_date": posted.isoformat(),
            "closes_on": closes, "source": "careers_page" if rng.random() < 0.45 else "job_board",
            "tools": ";".join(tools), "description": " ".join(text)}


def build(seed=SEED):
    """Return {"postings": [...], "app_log": [...], "profile": {...}} as text rows, like the CSVs."""
    rng = random.Random(seed)
    postings = []
    n = 230
    for i in range(1, n + 1):
        postings.append(make_posting(rng, "P%04d" % i))
    # reposts: the same role saved again under a new id, a few days newer
    for src in rng.sample(postings[:], 14):
        copy = dict(src)
        copy["posting_id"] = "P%04d" % (len(postings) + 1)
        d = datetime.date.fromisoformat(src["posted_date"]) + datetime.timedelta(days=rng.randint(1, 9))
        copy["posted_date"] = min(d, PLAN_START - datetime.timedelta(days=1)).isoformat()
        copy["source"] = "job_board" if src["source"] == "careers_page" else "careers_page"
        postings.append(copy)

    # the first week's applications: mostly to India postings she could apply to, a few others
    pool = [p for p in postings if p["country"] == "IN" and p["work_mode"] != "remote"
            and p["posted_date"] >= (LOG_START - datetime.timedelta(days=30)).isoformat()]
    chosen = rng.sample(pool, min(17, len(pool)))
    channel_screen = {"job_board": 0.12, "careers_page": 0.3, "referral": 0.65}
    log = []
    for a, p in enumerate(chosen, start=1):
        app_id = "A%03d" % a
        channel = rng.choices(["job_board", "careers_page", "referral"], weights=[6, 4, 2])[0]
        day = LOG_START + datetime.timedelta(days=rng.randint(0, 5))
        events = [("applied", day)]
        if rng.random() < channel_screen[channel]:
            s = day + datetime.timedelta(days=rng.randint(1, 3))
            if s <= LOG_END:
                events.append(("phone_screen" if s < RENAME_DAY else "screen", s))
                if rng.random() < 0.45:
                    iv = s + datetime.timedelta(days=rng.randint(1, 3))
                    if iv <= LOG_END:
                        events.append(("interview", iv))
                elif rng.random() < 0.3:
                    rj = s + datetime.timedelta(days=rng.randint(1, 2))
                    if rj <= LOG_END:
                        events.append(("rejected", rj))
        elif rng.random() < 0.2:
            rj = day + datetime.timedelta(days=rng.randint(1, 4))
            if rj <= LOG_END:
                events.append(("rejected", rj))
        for ev, d in events:
            log.append({"application_id": app_id, "posting_id": p["posting_id"], "channel": channel,
                        "event": ev, "event_date": d.isoformat()})
            if rng.random() < 0.12:  # typed twice
                log.append({"application_id": app_id, "posting_id": p["posting_id"], "channel": channel,
                            "event": ev, "event_date": d.isoformat()})
    # two of last week's roles were reposted on 1 November under new ids: same role, new posting
    applied = sorted({r["posting_id"] for r in log})
    by_id = {p["posting_id"]: p for p in postings}
    reposted = [by_id[i] for i in applied if by_id[i]["city"] in PROFILE["onsite_cities"]
                and not by_id[i]["closes_on"]]
    for src in rng.sample(reposted, min(2, len(reposted))):
        copy = dict(src)
        copy["posting_id"] = "P%04d" % (len(postings) + 1)
        copy["posted_date"] = LOG_END.isoformat()
        postings.append(copy)
    postings.sort(key=lambda p: p["posting_id"])
    log.sort(key=lambda r: (r["event_date"], r["application_id"]))
    for i, r in enumerate(log, start=1):
        r["log_id"] = "L%03d" % i
    log = [{k: r[k] for k in LOG_FIELDS} for r in log]
    return {"postings": postings, "app_log": log, "profile": dict(PROFILE)}


def write(rows, fields, path):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main():
    os.makedirs(DATA, exist_ok=True)
    d = build(SEED)
    write(d["postings"], POSTING_FIELDS, os.path.join(DATA, "postings.csv"))
    write(d["app_log"], LOG_FIELDS, os.path.join(DATA, "app_log.csv"))
    with open(os.path.join(DATA, "profile.json"), "w") as f:
        json.dump(d["profile"], f, indent=2, sort_keys=True)
        f.write("\n")
    print("postings.csv %d rows, app_log.csv %d rows (synthetic)" % (len(d["postings"]), len(d["app_log"])))


if __name__ == "__main__":
    main()
