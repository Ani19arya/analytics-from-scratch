"""Build data/postings.csv: 450 SYNTHETIC job postings at Orrowind Commerce, a fictional large
online retailer, and data/labels.csv: what the generator meant each title to be.

Why synthetic: to measure how many analyst roles a search finds, you need the full list of
postings and the truth about each one. The real evidence in data/real_snapshot_2026-10-31.json
has the top titles at one real company and the market-wide role family counts, not every
posting. Every title and number in this file is invented by this script with a fixed seed.
The title MIX is loosely shaped like the real evidence (finance, business and operations
analyst titles are common, titles that say "Data Analyst" are rare), but the counts say
nothing about any real company.

labels.csv columns:
- core_title: the title with the level words, abbreviations and team name sorted out, as the
  generator built it (the answer normalise_title should give);
- family: the role family (data, business, bi, finance, operations, product, marketing),
  "other_analyst" for analyst work outside those families, "not_analyst" for everything else;
- relevant: 1 if a job seeker looking for analyst work wants to see it, else 0.

Run: python3 make_data.py
"""
import csv
import os
import random

DEFAULT_SEED = 1102
N_POSTINGS = 450
COMPANY = "Orrowind Commerce"

# (family, relevant, weight, [(raw core as written, core_title), ...])
# The raw core is how the posting writes it, before level words and team names are added.
TITLE_BANK = [
    ("finance", 1, 0.20, [("Financial Analyst", "financial analyst"), ("Finance Analyst", "finance analyst"),
                          ("FP&A Analyst", "financial planning and analysis analyst")]),
    ("business", 1, 0.17, [("Business Analyst", "business analyst"), ("Business Systems Analyst", "business systems analyst")]),
    ("bi", 1, 0.10, [("Business Intelligence Engineer", "business intelligence engineer"), ("BIE", "business intelligence engineer"),
                     ("BI Analyst", "business intelligence analyst"), ("Reporting Analyst", "reporting analyst")]),
    ("operations", 1, 0.12, [("Operations Analyst", "operations analyst"), ("Ops Analyst", "operations analyst"),
                             ("Supply Chain Analyst", "supply chain analyst"), ("Network Planning Analyst", "network planning analyst"),
                             ("Demand Planning Analyst", "demand planning analyst")]),
    ("data", 1, 0.06, [("Data Analyst", "data analyst"), ("Insights Analyst", "insights analyst")]),
    ("product", 1, 0.03, [("Product Analyst", "product analyst")]),
    ("marketing", 1, 0.03, [("Marketing Analyst", "marketing analyst")]),
    ("other_analyst", 1, 0.08, [("Pricing Analyst", "pricing analyst"), ("Risk Analyst", "risk analyst"),
                                ("Category Analyst", "category analyst"), ("Quantitative Analyst", "quantitative analyst")]),
    ("not_analyst", 0, 0.21, [("Program Manager", "program manager"), ("Data Engineer", "data engineer"),
                              ("Security Operations Analyst", "security operations analyst"), ("Security Analyst", "security analyst"),
                              ("Data Entry Specialist", "data entry specialist"), ("Data Center Technician", "data center technician"),
                              ("Supply Chain Manager", "supply chain manager"), ("Account Executive", "account executive")]),
]
TEAMS = ["Last Mile Analytics", "Retail Finance", "Data Platform", "Global Operations", "Ads", "Marketplace",
         "Risk & Compliance", "Customer Insights", "Fulfilment Network", "Cloud Regions"]
LEVEL_PREFIX = [("", 0.55), ("Senior ", 0.25), ("Sr. ", 0.08), ("Junior ", 0.04), ("Lead ", 0.08)]
LEVEL_SUFFIX = [("", 0.6), (" I", 0.1), (" II", 0.2), (" III", 0.1)]


def pick(pairs, rng):
    r, total = rng.random(), 0.0
    for value, w in pairs:
        total += w
        if r < total:
            return value
    return pairs[-1][0]


def build(seed=DEFAULT_SEED, n=N_POSTINGS):
    """Return {"postings": [...], "labels": [...]} for this seed. Nothing is written."""
    rng = random.Random(seed)
    families = [(fam, rel, opts) for fam, rel, _, opts in TITLE_BANK]
    weights = [w for _, _, w, _ in TITLE_BANK]
    postings, labels = [], []
    for i in range(1, n + 1):
        fam, rel, opts = pick(list(zip(families, weights)), rng)
        raw_core, core = rng.choice(opts)
        title = pick(LEVEL_PREFIX, rng) + raw_core + pick(LEVEL_SUFFIX, rng)
        style = rng.random()
        if style < 0.45:
            title += ", " + rng.choice(TEAMS)
        elif style < 0.55:
            title += " - " + rng.choice(TEAMS)
        elif style < 0.62:
            title += " (" + rng.choice(TEAMS) + ")"
        if rng.random() < 0.05:
            title = title.upper()
        pid = "T%04d" % i
        postings.append({"posting_id": pid, "company": COMPANY, "title": title})
        labels.append({"posting_id": pid, "core_title": core, "family": fam, "relevant": rel})
    return {"postings": postings, "labels": labels}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    d = build()
    for name, fields in (("postings", ["posting_id", "company", "title"]),
                         ("labels", ["posting_id", "core_title", "family", "relevant"])):
        with open(os.path.join(data, name + ".csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(d[name])
    print("wrote %d synthetic postings to %s" % (len(d["postings"]), data))


if __name__ == "__main__":
    main()
