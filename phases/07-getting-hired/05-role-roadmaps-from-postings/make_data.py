"""Build data/postings.csv: 600 SYNTHETIC analyst postings with a job title and a tool list,
and data/labels.csv: the role family the generator meant for each title.

Why synthetic: the real Real Analyst Jobs data drop in data/job-market/2026-10 counts tools
by COUNTRY, not by job title, so it cannot say how a BI analyst differs from a product
analyst. This file is a stand-in for posting-level data with titles, such as postings you
save yourself. Every title, tool mix and number in it is invented by this script, and the
tool chances below are made up to teach the method, not taken from any market.

The tool list is written the way the data drop's feed writes it: one comma separated list
per posting, with the same eight tools the drop counts plus a few it does not.

Run: python3 make_data.py
"""
import csv
import os
import random

DEFAULT_SEED = 705
N_POSTINGS = 600
SKILLS = ["SQL", "Python", "Excel", "Tableau", "Power BI", "Looker", "R", "dbt"]
EXTRA_TOOLS = ["Jira", "Snowflake", "Alteryx", "SAS", "Spark", "RStudio"]

FAMILY_MIX = {"data": 0.38, "business": 0.22, "bi": 0.16, "product": 0.14, "other": 0.10}

# Titles per family. Some are written to trip a careless rule:
# "Business Intelligence Analyst" is BI, not business; "Product Data Analyst" is product;
# "Production Planning Analyst" is not product.
TITLES = {
    "data": ["Data Analyst", "Junior Data Analyst", "Senior Data Analyst", "Data Analyst II",
             "Marketing Data Analyst", "People Analytics Analyst", "data analyst"],
    "business": ["Business Analyst", "Senior Business Analyst", "Business Systems Analyst",
                 "IT Business Analyst", "Business Data Analyst", "BUSINESS ANALYST"],
    "bi": ["BI Analyst", "Business Intelligence Analyst", "Senior Business Intelligence Analyst",
           "Power BI Analyst", "BI Reporting Analyst", "Business Intelligence Analyst II"],
    "product": ["Product Analyst", "Senior Product Analyst", "Product Data Analyst",
                "Growth Product Analyst", "Product Analytics Analyst"],
    "other": ["Financial Analyst", "Production Planning Analyst", "Supply Chain Analyst",
              "Credit Risk Analyst"],
}

# Made-up chance that a posting in the family lists each tool.
TOOL_CHANCE = {
    "data": {"SQL": 0.80, "Python": 0.55, "Excel": 0.50, "Tableau": 0.35, "Power BI": 0.30,
             "Looker": 0.10, "R": 0.18, "dbt": 0.08, "Snowflake": 0.10, "RStudio": 0.03},
    "business": {"SQL": 0.45, "Python": 0.12, "Excel": 0.75, "Tableau": 0.12, "Power BI": 0.22,
                 "Looker": 0.03, "R": 0.03, "dbt": 0.01, "Jira": 0.40, "SAS": 0.05},
    "bi": {"SQL": 0.78, "Python": 0.20, "Excel": 0.45, "Tableau": 0.50, "Power BI": 0.70,
           "Looker": 0.18, "R": 0.03, "dbt": 0.15, "Alteryx": 0.10, "Snowflake": 0.12},
    "product": {"SQL": 0.88, "Python": 0.55, "Excel": 0.25, "Tableau": 0.25, "Power BI": 0.08,
                "Looker": 0.35, "R": 0.15, "dbt": 0.20, "Snowflake": 0.15, "Spark": 0.05},
    "other": {"SQL": 0.30, "Python": 0.15, "Excel": 0.85, "Tableau": 0.10, "Power BI": 0.25,
              "Looker": 0.02, "R": 0.05, "dbt": 0.00, "SAS": 0.15},
}
NO_TOOL_CHANCE = 0.15
CASE_VARIANTS = {"SQL": ["SQL", "sql"], "Power BI": ["Power BI", "power bi", "POWER BI"], "dbt": ["dbt", "DBT"]}


def pick(weights, rng):
    r, total = rng.random(), 0.0
    for key, w in weights.items():
        total += w
        if r < total:
            return key
    return key


def build(seed=DEFAULT_SEED, n=N_POSTINGS):
    """Return {"postings": [...], "labels": [...]} for this seed. Nothing is written."""
    rng = random.Random(seed)
    postings, labels = [], []
    for i in range(1, n + 1):
        family = pick(FAMILY_MIX, rng)
        title = rng.choice(TITLES[family])
        tools = []
        if rng.random() >= NO_TOOL_CHANCE:
            for tool, chance in TOOL_CHANCE[family].items():
                if rng.random() < chance:
                    tools.append(rng.choice(CASE_VARIANTS.get(tool, [tool])))
            if tools and rng.random() < 0.05:
                tools.append(tools[0].lower())  # the same tool listed twice
            rng.shuffle(tools)
        pid = "P%04d" % i
        postings.append({"posting_id": pid, "title": title, "tools": ", ".join(tools)})
        labels.append({"posting_id": pid, "family": family})
    return {"postings": postings, "labels": labels}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    d = build()
    for name, fields in (("postings", ["posting_id", "title", "tools"]), ("labels", ["posting_id", "family"])):
        with open(os.path.join(data, name + ".csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(d[name])
    print("wrote", data)


if __name__ == "__main__":
    main()
