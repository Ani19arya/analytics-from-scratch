"""Solution: where are the analyst roles you can get, and which 30 companies go on your list?

Part 1 reads the REAL data drop (data/job-market/2026-10, 25 October 2026) to choose countries.
Part 2 scores the companies in a SYNTHETIC set of saved postings to build a target list.
"""
import csv
import datetime
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LESSON = os.path.dirname(HERE) if os.path.basename(HERE) == "solution" else HERE
DATA = os.path.join(LESSON, "data")
DROP_DIR = os.path.join(LESSON, "..", "..", "..", "data", "job-market", "2026-10")
MIN_POSTINGS = 30
NOT_A_COUNTRY = {"UNKNOWN"}
AS_OF = "2026-10-31"

PROFILE = {
    "countries": ["GB", "IE"],
    "levels": ["Entry Level", "Mid Level", "Not Specified"],
    "skills": ["SQL", "Excel", "Power BI", "Python"],
    "min_fit": 0.5,
    "max_age": 30,
    "as_of": AS_OF,
}


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_postings():
    return load_csv(os.path.join(DATA, "postings.csv"))


def load_drop(folder=DROP_DIR):
    """The three drop files as {country: {"postings", "companies", "levels": {label: n},
    "skills": {skill: n}, "any_tool": n}}."""
    drop = {}
    for r in load_csv(os.path.join(folder, "by_country.csv")):
        drop[r["country"]] = {"postings": int(r["postings"]), "companies": int(r["companies"]),
                              "levels": {}, "skills": {}, "any_tool": 0}
    for r in load_csv(os.path.join(folder, "by_country_seniority.csv")):
        drop[r["country"]]["levels"][r["experience"]] = int(r["postings"])
    for r in load_csv(os.path.join(folder, "by_country_skill.csv")):
        drop[r["country"]]["skills"][r["skill"]] = int(r["postings_listing_skill"])
        drop[r["country"]]["any_tool"] = int(r["postings_listing_any_tool"])
    return drop


# ---------- Part 1: countries, from the real drop ----------

def where_to_look(drop, levels, min_postings=MIN_POSTINGS):
    rows = []
    for country, c in drop.items():
        if country in NOT_A_COUNTRY or c["postings"] < min_postings:
            continue
        at_level = sum(c["levels"].get(lv, 0) for lv in levels)
        labelled = c["postings"] - c["levels"].get("Not Specified", 0)
        labelled_at_level = sum(c["levels"].get(lv, 0) for lv in levels if lv != "Not Specified")
        rows.append({"country": country, "postings": c["postings"], "companies": c["companies"],
                     "at_level": at_level,
                     "share_of_labelled": None if labelled == 0 else 100.0 * labelled_at_level / labelled})
    rows.sort(key=lambda r: (-r["at_level"], r["country"]))
    return rows


def skill_share(drop, country, skill):
    c = drop.get(country)
    if c is None or c["any_tool"] == 0:
        return None
    return 100.0 * c["skills"].get(skill, 0) / c["any_tool"]


# ---------- Part 2: companies, from saved postings ----------

def parse_skills(cell):
    return {item.strip().lower() for item in (cell or "").split(",") if item.strip()}


def skill_fit(posting_skills, my_skills):
    if not posting_skills:
        return None
    mine = {s.lower() for s in my_skills}
    return len(posting_skills & mine) / len(posting_skills)


def age_days(posted_date, as_of):
    return (datetime.date.fromisoformat(as_of) - datetime.date.fromisoformat(posted_date)).days


def role_key(p):
    return (p["company"], " ".join(p["title"].lower().split()), p["country"])


def dedupe(postings):
    """One row per role (company, title ignoring case and spaces, country), keeping the earliest
    posted_date: that is when the role was first seen."""
    first = {}
    for p in postings:
        k = role_key(p)
        if k not in first or p["posted_date"] < first[k]["posted_date"]:
            first[k] = p
    return list(first.values())


def is_match(p, profile):
    if p["country"] not in profile["countries"] or p["seniority"] not in profile["levels"]:
        return False
    age = age_days(p["posted_date"], profile["as_of"])
    if age < 0 or age > profile["max_age"]:
        return False
    fit = skill_fit(parse_skills(p["skills"]), profile["skills"])
    return fit is None or fit >= profile["min_fit"]


def score_companies(postings, profile):
    by_company = {}
    for p in dedupe(postings):
        if is_match(p, profile):
            by_company.setdefault(p["company"], []).append(p)
    out = []
    for company, roles in by_company.items():
        fits = [skill_fit(parse_skills(p["skills"]), profile["skills"]) for p in roles]
        mean_fit = sum(0.5 if f is None else f for f in fits) / len(fits)
        newest = min(age_days(p["posted_date"], profile["as_of"]) for p in roles)
        score = 40 * mean_fit + 30 * max(0.0, 1 - newest / 30) + 30 * min(len(roles), 5) / 5
        out.append({"company": company, "roles": len(roles), "mean_fit": mean_fit,
                    "newest_age": newest, "score": score})
    out.sort(key=lambda r: (-round(r["score"], 6), -r["roles"], r["newest_age"], r["company"]))
    return out


def target_list(postings, profile, n=30):
    return score_companies(postings, profile)[:n]


if __name__ == "__main__":
    drop = load_drop()
    for r in where_to_look(drop, ["Entry Level", "Mid Level"])[:5]:
        print(r)
    for r in target_list(load_postings(), PROFILE)[:5]:
        print(r)
