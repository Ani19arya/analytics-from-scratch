"""Lesson 07 solution: page through a JSON API, retry politely, flatten, dedupe, count.

Run: python3 solution/solution.py   (offline: it reads the recorded pages in data/)
"""
import json
import os
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
LIMIT = 50
RETRY_STATUSES = {429, 500, 502, 503, 504}


# ---- done for you: the recorded feed, a fake fetch and a fake clock -------------

def load_recorded(folder=DATA):
    """Read data/pages/offset_*.json and data/failures.json into the shape build() returns."""
    pages = {}
    pages_dir = os.path.join(folder, "pages")
    for name in sorted(os.listdir(pages_dir)):
        if name.endswith(".json"):
            with open(os.path.join(pages_dir, name)) as f:
                body = json.load(f)
            pages[body["offset"]] = body
    failures = {}
    path = os.path.join(folder, "failures.json")
    if os.path.exists(path):
        with open(path) as f:
            failures = {int(k): v for k, v in json.load(f).items()}
    return {"pages": pages, "failures": failures}


class FakeFeed:
    """Plays back recorded responses. fetch(offset, limit) returns (status, headers, body),
    like a real HTTP call would, without touching the network."""

    def __init__(self, recorded):
        self.pages = recorded["pages"]
        self.failures = {k: list(v) for k, v in recorded.get("failures", {}).items()}
        self.calls = []

    def fetch(self, offset, limit):
        self.calls.append(offset)
        if self.pages and limit != next(iter(self.pages.values()))["limit"]:
            raise ValueError("this recording was made with limit=%d" % next(iter(self.pages.values()))["limit"])
        if self.failures.get(offset):
            r = self.failures[offset].pop(0)
            return r["status"], r["headers"], r["body"]
        if offset in self.pages:
            return 200, {}, self.pages[offset]
        total = max([p["total"] for p in self.pages.values()] or [0])
        return 200, {}, {"total": total, "limit": limit, "offset": offset, "jobs": []}


class FakeClock:
    """Records every sleep instead of waiting, so a test with retries runs instantly."""

    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


# ---- the lesson -----------------------------------------------------------------

def header(headers, name):
    """HTTP header names are case-insensitive: Retry-After and retry-after are the same."""
    for k, v in (headers or {}).items():
        if k.lower() == name.lower():
            return v
    return None


def fetch_with_retry(fetch, offset, limit, clock, max_attempts=4):
    """Return the body of a 200 response. Retry 429 and 5xx: wait Retry-After seconds
    if the server says so, else 1, 2, 4 ... seconds. Any other status fails at once."""
    for attempt in range(1, max_attempts + 1):
        status, headers, body = fetch(offset, limit)
        if status == 200:
            return body
        if status not in RETRY_STATUSES:
            raise RuntimeError("offset %d: HTTP %d, not retrying" % (offset, status))
        if attempt == max_attempts:
            break
        wait = header(headers, "Retry-After")
        clock.sleep(float(wait) if wait is not None else float(2 ** (attempt - 1)))
    raise RuntimeError("offset %d: gave up after %d attempts" % (offset, max_attempts))


def fetch_all(fetch, clock, limit=LIMIT, max_pages=1000):
    """Every job record from every page, in the order received (repeats included).
    Stop on a short or empty page, not on the first page's total."""
    jobs, offset = [], 0
    for _ in range(max_pages):
        body = fetch_with_retry(fetch, offset, limit, clock)
        batch = body.get("jobs") or []
        jobs.extend(batch)
        if len(batch) < limit:
            return jobs
        offset += limit
    raise RuntimeError("more than %d pages: is the feed looping?" % max_pages)


def dedupe(jobs):
    """Keep the first record for each slug. Pages overlap when the feed shifts."""
    seen, out = set(), []
    for job in jobs:
        key = job.get("slug")
        if key in seen:
            continue
        seen.add(key)
        out.append(job)
    return out


def flatten(job):
    """One flat row per job. Missing or null nested fields become None, never a crash."""
    company = job.get("company") or {}
    location = job.get("location") or {}
    salary = job.get("salary") or {}
    posted = job.get("postedAt")
    return {
        "slug": job.get("slug"),
        "title": job.get("title"),
        "company": company.get("name"),
        "country": location.get("country") or "UNKNOWN",
        "posted_date": datetime.strptime(posted, "%Y-%m-%dT%H:%M:%SZ").date() if posted else None,
        "salary_min": salary.get("min"),
        "tools": list(job.get("tools") or []),
    }


def count_week(rows, monday):
    """Roles posted from monday to the Sunday after it (UTC dates), total and by country.
    no_date counts rows with no postedAt at all, which no week can claim."""
    sunday = monday + timedelta(days=6)
    by_country = {}
    for r in rows:
        d = r["posted_date"]
        if d is not None and monday <= d <= sunday:
            by_country[r["country"]] = by_country.get(r["country"], 0) + 1
    return {"total": sum(by_country.values()), "by_country": by_country,
            "no_date": sum(1 for r in rows if r["posted_date"] is None)}


def main(folder=DATA, monday=date(2026, 10, 19)):
    feed, clock = FakeFeed(load_recorded(folder)), FakeClock()
    raw = fetch_all(feed.fetch, clock)
    rows = [flatten(j) for j in dedupe(raw)]
    week = count_week(rows, monday)
    print("requests: %d, waited %s seconds" % (len(feed.calls), clock.sleeps))
    print("records received: %d, unique roles: %d" % (len(raw), len(rows)))
    print("posted %s to %s: %d roles" % (monday, monday + timedelta(days=6), week["total"]))
    for country, n in sorted(week["by_country"].items(), key=lambda kv: (-kv[1], kv[0])):
        print("  %-8s %d" % (country, n))
    print("no posted date: %d" % week["no_date"])
    return week


if __name__ == "__main__":
    main()
