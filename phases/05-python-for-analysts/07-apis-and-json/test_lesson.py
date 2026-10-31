"""Tests for lesson 07: APIs and JSON.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

Offline only: the feed is a recording in data/, played back by FakeFeed, and every wait
goes through FakeClock, so nothing sleeps and nothing touches the network. Expected
numbers are computed here straight from the JSON files, on the committed recording and on
a second one that make_data.build(seed=2031) makes in memory.
"""
import importlib.util
import json
import os
import unittest
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" \
    else os.path.join(HERE, "exercise.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lesson = load("lesson", TARGET)
make_data = load("make_data", os.path.join(HERE, "make_data.py"))
OTHER_SEED = 2031
MONDAY = date(2026, 10, 19)


def read_committed():
    pages = {}
    folder = os.path.join(HERE, "data", "pages")
    for name in sorted(os.listdir(folder)):
        with open(os.path.join(folder, name)) as f:
            body = json.load(f)
        pages[body["offset"]] = body
    with open(os.path.join(HERE, "data", "failures.json")) as f:
        failures = {int(k): v for k, v in json.load(f).items()}
    return {"pages": pages, "failures": failures}


def expected(recorded, monday=MONDAY):
    """Walk the pages in offset order, keep the first record per slug, count by hand."""
    seen, raw, unique = set(), 0, []
    for offset in sorted(recorded["pages"]):
        for job in recorded["pages"][offset]["jobs"]:
            raw += 1
            if job["slug"] not in seen:
                seen.add(job["slug"])
                unique.append(job)
    by_country, no_date = {}, 0
    for job in unique:
        if job["postedAt"] is None:
            no_date += 1
            continue
        d = datetime.strptime(job["postedAt"][:10], "%Y-%m-%d").date()
        if monday <= d <= monday + timedelta(days=6):
            loc = job["location"] or {}
            c = loc.get("country") or "UNKNOWN"
            by_country[c] = by_country.get(c, 0) + 1
    sleeps = []
    for offset in sorted(recorded["failures"]):
        for attempt, r in enumerate(recorded["failures"][offset], 1):
            ra = r["headers"].get("Retry-After")
            sleeps.append(float(ra) if ra is not None else float(2 ** (attempt - 1)))
    return {"raw": raw, "unique": len(unique), "by_country": by_country,
            "total": sum(by_country.values()), "no_date": no_date, "sleeps": sleeps}


def scripted(responses):
    """A fetch that returns the given (status, headers, body) tuples in order."""
    queue = list(responses)
    calls = []

    def fetch(offset, limit):
        calls.append(offset)
        return queue.pop(0)
    fetch.calls = calls
    return fetch


def page(jobs, offset=0, limit=50):
    return (200, {}, {"total": len(jobs), "limit": limit, "offset": offset, "jobs": jobs})


class FeedChecks:
    recorded = None

    def run_pipeline(self):
        feed, clock = lesson.FakeFeed(self.recorded), lesson.FakeClock()
        raw = lesson.fetch_all(feed.fetch, clock)
        rows = [lesson.flatten(j) for j in lesson.dedupe(raw)]
        return feed, clock, raw, rows

    def test_every_page_and_every_wait(self):
        want = expected(self.recorded)
        feed, clock, raw, rows = self.run_pipeline()
        self.assertEqual(len(raw), want["raw"], "fetch_all should return every record from every page; "
                         "did you stop after page 1 or before the short last page?")
        self.assertEqual(clock.sleeps, want["sleeps"], "waits should be Retry-After when given, else 1, 2, 4 seconds")
        self.assertEqual(sorted(set(feed.calls)), sorted(self.recorded["pages"]),
                         "fetch_all should request each recorded offset, in steps of the page size")

    def test_dedupe_and_week_count(self):
        want = expected(self.recorded)
        _, _, raw, rows = self.run_pipeline()
        self.assertEqual(len(rows), want["unique"], "pages overlap when the feed shifts: keep one record per slug")
        got = lesson.count_week(rows, MONDAY)
        self.assertEqual(got["by_country"], want["by_country"], "count roles posted Monday to Sunday by country, "
                         "with UNKNOWN for a missing location or country")
        self.assertEqual(got["total"], want["total"])
        self.assertEqual(got["no_date"], want["no_date"])


class TestCommittedRecording(FeedChecks, unittest.TestCase):
    recorded = read_committed()

    def test_loader_matches_the_files(self):
        self.assertEqual(sorted(lesson.load_recorded()["pages"]), sorted(self.recorded["pages"]))


class TestSecondRecording(FeedChecks, unittest.TestCase):
    recorded = make_data.build(OTHER_SEED)


class TestSmallCases(unittest.TestCase):
    def job(self, slug, **kw):
        base = {"slug": slug, "title": "Data Analyst", "company": {"name": "Co"},
                "location": {"city": "Pune", "country": "IN"}, "postedAt": "2026-10-20T09:00:00Z",
                "salary": None, "tools": ["SQL"]}
        base.update(kw)
        return base

    def test_empty_feed(self):
        clock = lesson.FakeClock()
        self.assertEqual(lesson.fetch_all(scripted([page([])]), clock), [])
        self.assertEqual(lesson.count_week([], MONDAY), {"total": 0, "by_country": {}, "no_date": 0})

    def test_exactly_one_full_page(self):
        jobs = [self.job("j%d" % i) for i in range(50)]
        fetch = scripted([page(jobs), page([], offset=50)])
        self.assertEqual(len(lesson.fetch_all(fetch, lesson.FakeClock())), 50)
        self.assertEqual(fetch.calls, [0, 50], "a full page means there may be more: ask for the next offset")

    def test_nulls_do_not_crash(self):
        row = lesson.flatten(self.job("a", location=None, salary=None, postedAt=None, company=None, tools=None))
        self.assertEqual(row["country"], "UNKNOWN")
        self.assertIsNone(row["posted_date"])
        self.assertIsNone(row["salary_min"])
        self.assertIsNone(row["company"])
        self.assertEqual(row["tools"], [])
        inner = lesson.flatten(self.job("b", location={"city": None, "country": None}, salary={"min": 0, "max": 10}))
        self.assertEqual(inner["country"], "UNKNOWN")
        self.assertEqual(inner["salary_min"], 0, "a salary of 0 is a value, not a missing one")
        self.assertEqual(lesson.flatten(self.job("c"))["posted_date"], date(2026, 10, 20))

    def test_dedupe_keeps_first(self):
        a1, b, a2 = self.job("a", title="first"), self.job("b"), self.job("a", title="second")
        self.assertEqual([j["title"] for j in lesson.dedupe([a1, b, a2])], ["first", "Data Analyst"])

    def test_week_edges(self):
        rows = [lesson.flatten(self.job(s, postedAt=p)) for s, p in
                [("mon", "2026-10-19T00:00:00Z"), ("sun", "2026-10-25T23:59:59Z"),
                 ("before", "2026-10-18T23:59:59Z"), ("after", "2026-10-26T00:00:00Z"), ("none", None)]]
        got = lesson.count_week(rows, MONDAY)
        self.assertEqual(got["total"], 2, "Monday 00:00 and Sunday 23:59 are both in the week, the days either side are not")
        self.assertEqual(got["no_date"], 1)

    def test_retry_rules(self):
        clock = lesson.FakeClock()
        fetch = scripted([(429, {"retry-after": "0"}, {}), (503, {}, {}), page([])])
        self.assertEqual(lesson.fetch_with_retry(fetch, 0, 50, clock)["jobs"], [])
        self.assertEqual(clock.sleeps, [0.0, 2.0], "header names are case-insensitive; with no header, "
                         "the second attempt waits 2 seconds")
        clock = lesson.FakeClock()
        with self.assertRaises(RuntimeError):
            lesson.fetch_with_retry(scripted([(404, {}, {})]), 0, 50, clock)
        self.assertEqual(clock.sleeps, [], "a 404 will not fix itself: fail at once, do not wait and retry")
        clock = lesson.FakeClock()
        with self.assertRaises(RuntimeError):
            lesson.fetch_with_retry(scripted([(500, {}, {})] * 4), 0, 50, clock, max_attempts=4)
        self.assertEqual(clock.sleeps, [1.0, 2.0, 4.0], "4 attempts means 3 waits: 1, 2, 4 seconds, then give up")


if __name__ == "__main__":
    unittest.main()
