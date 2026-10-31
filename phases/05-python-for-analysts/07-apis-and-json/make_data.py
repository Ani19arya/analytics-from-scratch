"""Build data/: a synthetic, recorded job-feed API response, one JSON file per page.

The feed pages with ?limit=50&offset=N, newest posting first. While the pages were
being "recorded", a few new postings arrived at the top of the feed, so later pages
start a little earlier and repeat the last postings of the page before. Two requests
also failed the first time: one with 429 (rate limited, with a Retry-After header)
and one with 503 twice (no header). Everything is synthetic: no request was made to
any real API, and every company name is invented.

    python3 make_data.py     # writes data/pages/*.json, data/failures.json, data/fixture.json
    build(seed)              # returns {"pages": {offset: body}, "failures": {offset: [responses]}}
"""
import json
import os
import random
from datetime import datetime, timedelta

DEFAULT_SEED = 507
LIMIT = 50
RECORDED_AT = datetime(2026, 10, 26, 7, 0)  # Monday morning, UTC
SECTORS = ["Retail", "Bank", "Health", "Freight", "Media", "Energy", "Travel", "Software"]
TITLES = ["Data Analyst", "Senior Data Analyst", "Business Analyst", "Product Analyst",
          "BI Analyst", "Marketing Analyst", "Analytics Engineer", "Junior Data Analyst"]
PLACES = [("New York", "US"), ("Austin", "US"), ("Chicago", "US"), ("Seattle", "US"),
          ("Bengaluru", "IN"), ("Pune", "IN"), ("Hyderabad", "IN"),
          ("London", "GB"), ("Manchester", "GB"), ("Toronto", "CA"), ("Berlin", "DE")]
TOOLS = ["SQL", "Python", "Excel", "Tableau", "Power BI", "Looker", "R", "dbt"]


def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def make_job(rng, n, posted):
    company = "%s Co %02d" % (rng.choice(SECTORS), rng.randint(1, 40))
    title = rng.choice(TITLES)
    roll = rng.random()
    if roll < 0.12:
        location = None                                   # remote: no location object at all
    elif roll < 0.18:
        location = {"city": None, "country": None}        # location object with nulls inside
    else:
        city, country = rng.choice(PLACES)
        location = {"city": city, "country": country}
    salary = None
    if rng.random() < 0.3:
        low = rng.randrange(50, 130) * 1000
        salary = {"min": low, "max": low + rng.randrange(10, 40) * 1000, "currency": "USD"}
    return {
        "slug": "%s-%s-%04d" % (title.lower().replace(" ", "-"), company.lower().replace(" ", "-"), n),
        "title": title,
        "company": {"name": company, "website": None if rng.random() < 0.2 else
                    "https://example.com/%s" % company.lower().replace(" ", "-")},
        "location": location,
        "postedAt": None if posted is None else stamp(posted),
        "salary": salary,
        "tools": rng.sample(TOOLS, rng.randint(0, 4)),
    }


def build(seed=DEFAULT_SEED):
    rng = random.Random(seed)
    n_jobs = rng.randint(225, 275)
    jobs = []
    for n in range(n_jobs):
        if rng.random() < 0.06:
            posted = None
        else:
            posted = RECORDED_AT - timedelta(days=rng.randint(1, 21), minutes=rng.randint(0, 1439))
        jobs.append(make_job(rng, n, posted))
    # The feed sorts newest first, postings with no date last.
    dated = sorted([j for j in jobs if j["postedAt"]], key=lambda j: j["postedAt"], reverse=True)
    feed = dated + [j for j in jobs if not j["postedAt"]]

    pages, offset, extra = {}, 0, n_jobs
    while True:
        if offset > 0:
            for _ in range(rng.choice([0, 1, 1, 2, 3])):   # new postings arrive while we page
                fresh = RECORDED_AT + timedelta(minutes=rng.randint(1, 50))
                feed.insert(0, make_job(rng, extra, fresh))
                extra += 1
        batch = feed[offset:offset + LIMIT]
        pages[offset] = {"total": len(feed), "limit": LIMIT, "offset": offset, "jobs": batch}
        if len(batch) < LIMIT:
            break
        offset += LIMIT
    failures = {
        100: [{"status": 429, "headers": {"Retry-After": str(rng.choice([1, 2, 3]))},
               "body": {"error": "rate limited"}}],
        200: [{"status": 503, "headers": {}, "body": {"error": "service unavailable"}},
              {"status": 503, "headers": {}, "body": {"error": "service unavailable"}}],
    }
    return {"pages": pages, "failures": failures}


def write_json(path, obj):
    with open(path, "w", newline="\n") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
        f.write("\n")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    pages_dir = os.path.join(data, "pages")
    os.makedirs(pages_dir, exist_ok=True)
    for name in os.listdir(pages_dir):
        if name.endswith(".json"):
            os.remove(os.path.join(pages_dir, name))
    built = build()
    for offset, body in built["pages"].items():
        write_json(os.path.join(pages_dir, "offset_%04d.json" % offset), body)
    write_json(os.path.join(data, "failures.json"), {str(k): v for k, v in built["failures"].items()})
    write_json(os.path.join(data, "fixture.json"), {
        "what": "A recorded response from a job-feed API, paged with limit and offset.",
        "source": "synthetic: built by make_data.py with seed %d. No request was made to any real API." % DEFAULT_SEED,
        "recorded_at": stamp(RECORDED_AT),
        "shape_note": "Shaped like a typical JSON feed. The public feed at https://realanalystjobs.com/api/job-feed is flatter; this one is nested on purpose.",
        "pages": len(built["pages"]),
        "limit": LIMIT,
    })
    print("wrote", len(built["pages"]), "pages,", sum(len(b["jobs"]) for b in built["pages"].values()), "job records")


if __name__ == "__main__":
    main()
