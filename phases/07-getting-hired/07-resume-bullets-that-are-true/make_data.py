"""Build data/resume.txt and data/evidence.csv for the resume claims lesson.

resume.txt: a resume. A heading line that ends with "(project-id)" starts a project; the
            "- " bullets under it are claims about that project.
evidence.csv: project, metric, unit, from_value, to_value, source.
            One row per number the candidate can show. unit is number, pct (a rate in
            percent) or pts (a gap in percentage points). from_value is blank for a single fact;
            when it is filled, the row is a comparison from from_value to to_value.

The committed files are hand written (seed 0): Maya Okafor's resume, with her internship at
Lumen Freight (from lesson 04) and two course projects (lessons 03 and 06). The numbers in
the evidence rows for those projects are the ones the lessons computed. Maya, Lumen Freight
and every number are invented.
Any other seed generates a new resume and evidence file, for the second-dataset test.
Run from the lesson folder: python3 make_data.py
In code: build(seed) returns {"resume": text, "evidence": rows} without writing files.
"""
import csv
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 0
HEADER = ["project", "metric", "unit", "from_value", "to_value", "source"]

RESUME = """Maya Okafor
Data analyst, Pune

Summary
- Saved teams over 100 hours of manual reporting.

Experience
Analyst intern, Lumen Freight (lumen-freight)
- Built a PowerBI dashboard for late deliveries used by 30 depot managers.
- Automated the weekly late-delivery report in Python, cutting it from 6.5 to 4.25 hours, a 40% saving.
- Ran an A/B test on payment reminder emails that lifted on-time payment by 3.2%.

Projects
Pantrybox churn analysis (pantrybox-churn)
- Analysed 1,400 subscriptions and found that 224 of 779 trial starters (28.8%) never paid.
- Showed that trial converters churn 4.6% more than paid starters within 90 days of paying.

Tiffinbell dispatch test (tiffinbell-dispatch)
- Measured a 4.0 point rise in on-time deliveries, from 80.5% to 84.5%, across 1,771 orders.
"""

EVIDENCE = [
    ["lumen-freight", "depot managers using the dashboard", "number", "", "30", "dashboard viewer log, September 2026"],
    ["lumen-freight", "hours to build the weekly report", "number", "6.5", "4.25", "time sheet, 4 weeks before and after"],
    ["lumen-freight", "on-time payment rate, old email to new email", "pct", "61.0", "64.2", "A/B test write-up"],
    ["pantrybox-churn", "customers analysed", "number", "", "1400", "lesson 07-03, data/subscriptions.csv"],
    ["pantrybox-churn", "trial starters with the whole trial", "number", "", "779", "lesson 07-03 write-up, Result"],
    ["pantrybox-churn", "trial starters who never paid", "number", "", "224", "lesson 07-03 write-up, Result"],
    ["pantrybox-churn", "never paid rate", "pct", "", "28.8", "lesson 07-03 write-up, Result"],
    ["pantrybox-churn", "90 day paid churn, paid starters to trial converters", "pct", "18.3", "22.9", "lesson 07-03 write-up, Result"],
    ["pantrybox-churn", "90 day churn window in days", "number", "", "90", "lesson 07-03 write-up, Method"],
    ["tiffinbell-dispatch", "on-time rate, current rule to new rule", "pct", "80.5", "84.5", "lesson 07-06 data/results.csv"],
    ["tiffinbell-dispatch", "orders in the test", "number", "", "1771", "lesson 07-06 data/orders.csv"],
]

# For generated data
PROJECTS = ["basket-size", "refund-delays", "signup-funnel", "store-footfall", "ticket-backlog", "trial-offer"]
NUMBER_METRICS = ["hours per week on the report", "minutes to refresh the dashboard", "manual steps in the pipeline",
                  "open support tickets", "days to close the books"]
RATE_METRICS = ["conversion rate", "repeat purchase rate", "on-time rate", "refund rate", "open rate"]


def fmt(x, places):
    return ("%." + str(places) + "f") % x


def generate(seed):
    """A resume and evidence rows with true, rounded, inflated and mislabelled claims."""
    rng = random.Random(seed)
    evidence = []
    lines = ["Sample Candidate", "Analyst", "", "Summary",
             "- Delivered %d%% faster insight for the whole team." % rng.randint(20, 60), "", "Projects"]
    for project in rng.sample(PROJECTS, 3):
        lines.append("%s (%s)" % (project.replace("-", " ").capitalize(), project))
        # one count comparison, one rate comparison, one single fact
        a = rng.randint(30, 90) / 2.0
        b = round(a * rng.uniform(0.4, 0.8), 1)
        r1 = rng.randint(150, 600) / 10.0
        r2 = round(r1 + rng.choice([-1, 1]) * rng.randint(15, 80) / 10.0, 1)
        n = rng.randint(200, 5000)
        m1, m2 = rng.choice(NUMBER_METRICS), rng.choice(RATE_METRICS)
        evidence.append([project, m1, "number", fmt(a, 1), fmt(b, 1), "generated"])
        evidence.append([project, m2, "pct", fmt(r1, 1), fmt(r2, 1), "generated"])
        evidence.append([project, "rows in the data", "number", "", str(n), "generated"])
        rel = abs(b - a) / a * 100
        pts = abs(r2 - r1)
        rel_rate = abs(r2 - r1) / r1 * 100
        choice = rng.randrange(4)
        if choice == 0:      # true and rounded to a whole number
            lines.append("- Cut the %s from %s to %s, a %s%% drop." % (m1, fmt(a, 1), fmt(b, 1), fmt(rel, 0)))
        elif choice == 1:    # inflated
            lines.append("- Cut the %s by %d%%." % (m1, int(rel) + rng.randint(4, 9)))
        elif choice == 2:    # understated: not a lie, but not what the evidence says
            lines.append("- Cut the %s by %d%%." % (m1, int(rel) - rng.randint(3, 6)))
        else:                # true, one decimal
            lines.append("- Cut the %s by %s%%." % (m1, fmt(rel, 1)))
        if rng.random() < 0.5:   # points written as percent
            lines.append("- Moved the %s by %s%%, across %s rows." % (m2, fmt(pts, 1), format(n, ",")))
        else:                    # points written as points, or the relative change
            lines.append("- Moved the %s from %s%% to %s%% (%s points, %s%%), across %d rows."
                         % (m2, fmt(r1, 1), fmt(r2, 1), fmt(pts, 1), fmt(rel_rate, 0), n))
        lines.append("")
    return {"resume": "\n".join(lines), "evidence": evidence}


def build(seed=SEED):
    """{"resume": text, "evidence": rows}. Seed 0 is the hand written lesson data."""
    if seed == SEED:
        return {"resume": RESUME, "evidence": [list(r) for r in EVIDENCE]}
    return generate(seed)


def main():
    data = build()
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(os.path.join(HERE, "data", "resume.txt"), "w") as f:
        f.write(data["resume"])
    with open(os.path.join(HERE, "data", "evidence.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(data["evidence"])
    print("wrote a resume and %d evidence rows" % len(data["evidence"]))


if __name__ == "__main__":
    main()
