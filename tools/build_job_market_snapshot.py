"""Build the monthly analyst job market data drop.

Pages through the public Real Analyst Jobs feed and writes aggregate CSVs
(no company or job level rows) into data/job-market/<YYYY-MM>/.

Usage:
    python3 tools/build_job_market_snapshot.py 2026-10-25
    python3 tools/build_job_market_snapshot.py 2026-10-25 --out data/job-market/2026-10

Standard library only. Python 3.9+.
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.request
from collections import defaultdict

FEED = "https://realanalystjobs.com/api/job-feed?limit={limit}&offset={offset}"
PAGE = 100
# Reposting sites: their listings duplicate roles posted elsewhere.
EXCLUDED_COMPANIES = {"jobgether", "weekday"}
SKILLS = ["SQL", "Python", "Excel", "Tableau", "Power BI", "Looker", "R", "dbt"]
USER_AGENT = "analytics-from-scratch-snapshot/1.0 (+https://realanalystjobs.com)"


def fetch_page(offset, retries=3):
    url = FEED.format(limit=PAGE, offset=offset)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # network hiccup: back off and retry
            if attempt == retries - 1:
                raise
            print("retry offset %d: %s" % (offset, exc), file=sys.stderr)
            time.sleep(2 * (attempt + 1))


def fetch_all():
    jobs = []
    offset = 0
    total = None
    while True:
        data = fetch_page(offset)
        batch = data.get("jobs") or []
        if total is None:
            total = data.get("total")
        jobs.extend(batch)
        offset += PAGE
        if not batch or (total is not None and offset >= total):
            break
        time.sleep(0.2)
    return jobs, total


def parse_stack(raw):
    if not raw:
        return set()
    return {part.strip().lower() for part in str(raw).split(",") if part.strip()}


def aggregate(jobs):
    """Return (country_rows, skill_rows, seniority_rows) as lists of dicts."""
    postings = defaultdict(int)
    companies = defaultdict(set)
    any_tool = defaultdict(int)
    skill_hits = defaultdict(int)
    seniority = defaultdict(int)
    seen = set()

    for job in jobs:
        company = (job.get("company") or "").strip()
        if company.lower() in EXCLUDED_COMPANIES:
            continue
        key = job.get("slug") or (company, job.get("title"), job.get("location"))
        if key in seen:  # guard against the live feed shifting between pages
            continue
        seen.add(key)
        country = (job.get("country") or "").strip().upper() or "UNKNOWN"
        postings[country] += 1
        if company:
            companies[country].add(company.lower())
        stack = parse_stack(job.get("techStack"))
        if stack:
            any_tool[country] += 1
            for skill in SKILLS:
                if skill.lower() in stack:
                    skill_hits[(country, skill)] += 1
        exp = (job.get("experience") or "").strip() or "Not Specified"
        seniority[(country, exp)] += 1

    order = sorted(postings, key=lambda c: (-postings[c], c))
    country_rows = [
        {"country": c, "postings": postings[c], "companies": len(companies[c])}
        for c in order
    ]
    skill_rows = []
    for c in order:
        base = any_tool[c]
        for skill in SKILLS:
            hits = skill_hits[(c, skill)]
            share = round(100.0 * hits / base, 1) if base else ""
            skill_rows.append({
                "country": c,
                "skill": skill,
                "postings_listing_skill": hits,
                "postings_listing_any_tool": base,
                "share_pct": share,
            })
    seniority_rows = []
    for c in order:
        levels = [(e, n) for (cc, e), n in seniority.items() if cc == c]
        for exp, n in sorted(levels, key=lambda x: (-x[1], x[0])):
            seniority_rows.append({"country": c, "experience": exp, "postings": n})
    return country_rows, skill_rows, seniority_rows


def write_csv(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("date", help="snapshot date, YYYY-MM-DD")
    parser.add_argument("--out", help="output folder (default data/job-market/YYYY-MM)")
    args = parser.parse_args(argv)

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = args.out or os.path.join(root, "data", "job-market", args.date[:7])
    os.makedirs(out, exist_ok=True)

    jobs, total = fetch_all()
    country_rows, skill_rows, seniority_rows = aggregate(jobs)

    write_csv(os.path.join(out, "by_country.csv"),
              ["country", "postings", "companies"], country_rows)
    write_csv(os.path.join(out, "by_country_skill.csv"),
              ["country", "skill", "postings_listing_skill",
               "postings_listing_any_tool", "share_pct"], skill_rows)
    write_csv(os.path.join(out, "by_country_seniority.csv"),
              ["country", "experience", "postings"], seniority_rows)

    kept = sum(r["postings"] for r in country_rows)
    print("snapshot date: %s" % args.date)
    print("feed total: %s, fetched: %d, kept after exclusions: %d"
          % (total, len(jobs), kept))
    print("rows: by_country=%d by_country_skill=%d by_country_seniority=%d"
          % (len(country_rows), len(skill_rows), len(seniority_rows)))
    for r in country_rows[:5]:
        print("  %s %d postings, %d companies" % (r["country"], r["postings"], r["companies"]))
    print("written to %s" % out)


if __name__ == "__main__":
    main()
