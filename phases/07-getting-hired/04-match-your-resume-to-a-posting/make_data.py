"""Build data/resume.txt and data/postings.csv for the resume matching lesson.

postings.csv: posting_id, company, title, text
The resume, the candidate and all five companies are invented. No real posting was copied.
The text is fixed (no randomness), so the output is the same on every run.
Run from the lesson folder: python3 make_data.py
"""
import csv
import os

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


def main():
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(os.path.join(HERE, "data", "resume.txt"), "w") as f:
        f.write(RESUME)
    with open(os.path.join(HERE, "data", "postings.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["posting_id", "company", "title", "text"])
        w.writerows(POSTINGS)
    print("wrote resume and %d postings" % len(POSTINGS))


if __name__ == "__main__":
    main()
