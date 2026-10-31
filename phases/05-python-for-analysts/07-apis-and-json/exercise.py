"""Exercise: page through a recorded JSON API, retry politely, flatten, dedupe, count.

load_recorded, FakeFeed, FakeClock, header and main are done for you.
Fill in the five functions marked TODO. Then run: python3 test_lesson.py
Run the whole thing: python3 exercise.py   (offline: it reads the recorded pages in data/)
"""
import json
import os
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
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
    """Call fetch(offset, limit), which returns (status, headers, body).
    200: return the body. 429 or 5xx: wait and try again, at most max_attempts calls in all.
    Wait the Retry-After header's seconds if present, else 1, 2, 4 ... seconds, always
    through clock.sleep(). Any other status: raise RuntimeError at once. Out of attempts:
    raise RuntimeError."""
    # TODO
    raise NotImplementedError


def fetch_all(fetch, clock, limit=LIMIT, max_pages=1000):
    """Every job record from every page, in the order received, repeats included."""
    # TODO: decide when to stop. Read the README before trusting "total".
    raise NotImplementedError


def dedupe(jobs):
    """Keep the first record for each slug."""
    # TODO
    raise NotImplementedError


def flatten(job):
    """One flat row: slug, title, company (the name), country ("UNKNOWN" if missing),
    posted_date (a date, or None), salary_min (or None), tools (a list)."""
    # TODO: location, salary and postedAt can each be null.
    raise NotImplementedError


def count_week(rows, monday):
    """{"total": n, "by_country": {country: n}, "no_date": n} for roles posted from monday
    to the Sunday after it. no_date counts every row with no posted date."""
    # TODO
    raise NotImplementedError


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
