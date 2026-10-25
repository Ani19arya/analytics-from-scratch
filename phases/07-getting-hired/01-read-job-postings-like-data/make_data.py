"""Build data/postings.csv and data/labels.csv: synthetic analyst job postings.

postings.csv: posting_id, company, title, country, text
labels.csv:   posting_id, tools, min_years, max_years, visa
  tools is a ';' separated list of what the generator put in the role text.
  min_years and max_years are blank when the posting states no experience.
  visa is one of yes, no, silent.

Every company, title and sentence is invented. No real posting was copied.
The labels exist only because we generated the text; a real feed has none,
which is why you build the extractor. The data is synthetic and deterministic.
Run from the lesson folder: python3 make_data.py
"""
import csv
import os
import random

random.seed(707)

HERE = os.path.dirname(os.path.abspath(__file__))
N = 300

PREFIX = ["Larkspur", "Quillon", "Tidewell", "Ambergate", "Corvane", "Halden", "Mirabay",
          "Pinefold", "Saltmarsh", "Veltrop", "Ironbark", "Glimmer", "Ostwick", "Redfern"]
SUFFIX = ["Analytics", "Health", "Retail", "Logistics", "Bank", "Foods", "Labs", "Insurance"]
TITLES = ["Data Analyst", "Junior Data Analyst", "Business Analyst", "Product Analyst",
          "Senior Data Analyst", "Marketing Analyst", "Operations Analyst"]

# Tool: (chance it appears in a posting, ways the posting may spell it)
TOOLS = {
    "SQL": (0.72, ["SQL", "advanced SQL", "SQL (PostgreSQL or MySQL)"]),
    "Python": (0.48, ["Python", "Python (pandas)"]),
    "Excel": (0.40, ["Excel", "Microsoft Excel", "advanced Excel"]),
    "Tableau": (0.33, ["Tableau"]),
    "Power BI": (0.28, ["Power BI", "PowerBI", "Power-BI"]),
    "R": (0.15, ["R", "R or Python"]),
    "Looker": (0.10, ["Looker"]),
    "dbt": (0.08, ["dbt"]),
}

BOILERPLATE = [
    "About us: {company} has helped clients for over {age} years. Our teams excel at turning data into decisions.",
    "About us: For {age} years {company} has grown with its customers. We excel at service and we hire people who care.",
]
EXPERIENCE = [
    ("{lo}+ years of experience in an analyst role.", "plus"),
    ("{lo}-{hi} years of experience with data.", "range"),
    ("{lo} to {hi} years of experience; new graduates welcome.", "range"),
    ("At least {lo} years of hands-on analytics work.", "plus"),
]
VISA = {
    "no": ["We are unable to sponsor work visas for this role.",
           "Candidates must be authorized to work without visa sponsorship.",
           "This role will not sponsor employment visas now or in the future."],
    "yes": ["Visa sponsorship is available for the right candidate.",
            "We sponsor H-1B visas for this position.",
            "We will consider visa sponsorship."],
}


def pick_tools(rng):
    chosen = [t for t, (p, _) in TOOLS.items() if rng.random() < p]
    if not chosen:
        chosen = ["SQL"]
    return chosen


def build():
    rng = random
    postings, labels = [], []
    for i in range(1, N + 1):
        company = "%s %s" % (rng.choice(PREFIX), rng.choice(SUFFIX))
        title = rng.choice(TITLES)
        country = "US" if rng.random() < 0.6 else "India"
        tools = pick_tools(rng)
        names = {t: rng.choice(TOOLS[t][1]) for t in tools}
        if "R" in tools and names["R"] == "R or Python" and "Python" not in tools:
            names["R"] = "R"
        required = tools[: max(1, len(tools) - 1)] if len(tools) > 1 else tools
        nice = [t for t in tools if t not in required]

        parts = [rng.choice(BOILERPLATE).format(company=company, age=rng.choice([12, 15, 20, 25, 40]))]
        parts.append("About the role: We are hiring a %s to build reports and answer questions for our %s team."
                     % (title, rng.choice(["R&D", "finance", "sales", "growth", "supply chain"])))

        lo = hi = None
        r = rng.random()
        if r < 0.85:
            template, kind = rng.choice(EXPERIENCE)
            if "Junior" in title or rng.random() < 0.15:
                lo = 0 if kind == "range" else 1
            elif "Senior" in title:
                lo = rng.choice([5, 6, 7])
            else:
                lo = rng.choice([1, 2, 2, 3, 3, 4])
            if kind == "range":
                hi = lo + rng.choice([2, 3])
            else:
                hi = None
            if lo == 0 and kind == "plus":
                lo = 1
            parts.append(template.format(lo=lo, hi=hi))
        parts.append("Requirements: " + ", ".join(names[t] for t in required) + ".")
        if nice:
            parts.append("Nice to have: " + ", ".join(names[t] for t in nice) + ".")
        parts.append("Reporting skills and clear writing matter.")

        v = rng.random()
        visa = "silent"
        if v < 0.12:
            visa = "no"
        elif v < 0.20:
            visa = "yes"
        if visa != "silent":
            parts.append(rng.choice(VISA[visa]))
        parts.append("Benefits: health cover, learning budget, flexible hours.")

        postings.append([i, company, title, country, " ".join(parts)])
        labels.append([i, ";".join(sorted(tools)), "" if lo is None else lo, "" if hi is None else hi, visa])
    return postings, labels


def main():
    postings, labels = build()
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(os.path.join(HERE, "data", "postings.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["posting_id", "company", "title", "country", "text"])
        w.writerows(postings)
    with open(os.path.join(HERE, "data", "labels.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["posting_id", "tools", "min_years", "max_years", "visa"])
        w.writerows(labels)
    print("wrote %d postings" % len(postings))


if __name__ == "__main__":
    main()
