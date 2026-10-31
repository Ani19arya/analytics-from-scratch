"""Build data/resume.txt and data/postings.csv for the resume matching lesson.

postings.csv: posting_id, company, title, text
The resume, the candidate and all five companies are invented. No real posting was copied.
The committed files are hand written (seed 0). Any other seed builds a different resume and
five postings from the same skill list, with random spellings, for the second-dataset test.
Run from the lesson folder: python3 make_data.py
In code: build(seed) returns {"resume": text, "postings": rows, "truth": the skills a careful
human reads in each text}, without writing files.
"""
import csv
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))

RESUME = """Maya Okafor
Data analyst, Pune

Skills: SQL (PostgreSQL), Python (pandas), PowerBI, Excel, statistics, A/B tests, GA4

Experience
Analyst intern, Lumen Freight (fictional), 2025 to 2026
- Built a PowerBI dashboard for late deliveries used by 30 depot managers.
- Wrote PostgreSQL queries to join shipment and invoice tables.
- Ran two A/B tests on reminder emails and wrote up the results.

Projects
- Churn analysis for a subscription business in Python with a two proportion test.
"""

POSTINGS = [
    ("P1", "Brightmoor Retail", "Data Analyst",
     "About us: we sell home goods across 40 stores and our R&D team designs every product.\n"
     "What you need: SQL, Power BI and Excel. Comfort with statistics.\n"
     "Nice to have: Python, Google Analytics."),
    ("P2", "Calloway Health", "Product Analyst",
     "About us: a clinic booking app.\n"
     "What you need: SQL, Python, A/B testing and Tableau.\n"
     "Nice to have: dbt, Looker."),
    ("P3", "Darnell Bank", "Risk Analyst",
     "About us: a regional bank. Reporting to the head of risk.\n"
     "What you need: SAS, SQL, statistics and Excel.\n"
     "Nice to have: R, machine learning."),
    ("P4", "Elmstead Media", "Marketing Analyst",
     "About us: a podcast network.\n"
     "What you need: Google Analytics, Excel, Power-BI.\n"
     "Nice to have: SQL, experimentation."),
    ("P5", "Fairhaven Logistics", "Senior Data Analyst",
     "About us: freight across three countries.\n"
     "What you need: SQL, Python, Snowflake, dbt and Looker.\n"
     "Nice to have: Power BI, statistics."),
]


SEED = 0
# What a careful human reads in the hand written files: resume skills, then for each posting
# (required, nice to have). Canonical names as in the lesson's synonym table.
TRUTH = {
    "resume": {"sql", "python", "power bi", "excel", "statistics", "a/b testing", "google analytics"},
    "P1": ({"sql", "power bi", "excel", "statistics"}, {"python", "google analytics"}),
    "P2": ({"sql", "python", "a/b testing", "tableau"}, {"dbt", "looker"}),
    "P3": ({"sas", "sql", "statistics", "excel"}, {"r", "machine learning"}),
    "P4": ({"google analytics", "excel", "power bi"}, {"sql", "a/b testing"}),
    "P5": ({"sql", "python", "snowflake", "dbt", "looker"}, {"power bi", "statistics"}),
}

# For generated data: canonical skill -> ways a person might write it.
SPELLINGS = {
    "sql": ["SQL", "PostgreSQL", "MySQL", "T-SQL"],
    "python": ["Python", "pandas"],
    "r": ["R"],
    "excel": ["Excel", "Microsoft Excel"],
    "power bi": ["Power BI", "PowerBI", "Power-BI"],
    "tableau": ["Tableau"],
    "looker": ["Looker"],
    "dbt": ["dbt"],
    "snowflake": ["Snowflake"],
    "sas": ["SAS"],
    "statistics": ["statistics", "statistical methods"],
    "a/b testing": ["A/B testing", "A/B tests", "experimentation"],
    "google analytics": ["Google Analytics", "GA4"],
    "machine learning": ["machine learning"],
}
COMPANIES = ["Ashcombe Foods", "Brackwater Freight", "Cindral Health", "Dunmere Media", "Eskdale Retail",
             "Farrowby Bank", "Glenrock Travel", "Holloway Learning"]
TITLES = ["Data Analyst", "Product Analyst", "Marketing Analyst", "Business Analyst", "Risk Analyst"]
BLURBS = ["About us: our R&D team designs every product.", "About us: you will be reporting to the CFO.",
          "About us: a small team that ships every week."]


def write_list(rng, skills):
    """'a, b and c' with a random spelling for each skill."""
    names = [rng.choice(SPELLINGS[s]) for s in skills]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def build(seed=SEED):
    """{"resume": text, "postings": [[id, company, title, text]], "truth": {...}}.
    Seed 0 is the hand written lesson data. Other seeds generate new data."""
    if seed == SEED:
        return {"resume": RESUME, "postings": [list(p) for p in POSTINGS], "truth": TRUTH}
    rng = random.Random(seed)
    skills = sorted(SPELLINGS)
    have = set(rng.sample(skills, rng.randint(4, 7)))
    resume = "Sample Candidate\nAnalyst\n\nSkills: %s\n" % write_list(rng, sorted(have))
    truth, postings = {"resume": have}, []
    for i in range(1, 6):
        pool = rng.sample(skills, rng.randint(3, 7))
        k = rng.randint(2, len(pool) - 1)
        required, nice = set(pool[:k]), set(pool[k:])
        text = (rng.choice(BLURBS) + "\nWhat you need: " + write_list(rng, pool[:k]) + "."
                + "\nNice to have: " + write_list(rng, pool[k:]) + ".")
        pid = "P%d" % i
        postings.append([pid, rng.choice(COMPANIES), rng.choice(TITLES), text])
        truth[pid] = (required, nice)
    return {"resume": resume, "postings": postings, "truth": truth}


def main():
    data = build()
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(os.path.join(HERE, "data", "resume.txt"), "w") as f:
        f.write(data["resume"])
    with open(os.path.join(HERE, "data", "postings.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["posting_id", "company", "title", "text"])
        w.writerows(data["postings"])
    print("wrote resume and %d postings" % len(data["postings"]))


if __name__ == "__main__":
    main()
