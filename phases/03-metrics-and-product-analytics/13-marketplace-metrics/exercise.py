"""Lesson 13: marketplace metrics and liquidity. Your turn.

Goal: measure liquidity from both sides of the marketplace, city by city, and say
which side is short. Definitions are in "The idea" in the README.
Standard library only. Fill in every TODO, then run: python3 test_lesson.py
"""
import csv
import datetime
import os

FMT = "%Y-%m-%d %H:%M"
AS_OF = datetime.datetime(2026, 11, 1, 0, 0)
ALL = "all"


# Given helpers.

def parse_time(text):
    """'2026-10-01 14:05' -> datetime; '' -> None."""
    return datetime.datetime.strptime(text, FMT) if text else None


def load(folder):
    """(posts, applications, searches) as lists of dicts with times parsed."""
    def read(name):
        with open(os.path.join(folder, name + ".csv"), newline="") as f:
            return list(csv.DictReader(f))
    posts = read("posts")
    for p in posts:
        p["posted_at"], p["closed_at"] = parse_time(p["posted_at"]), parse_time(p["closed_at"])
    apps = read("applications")
    for a in apps:
        a["applied_at"] = parse_time(a["applied_at"])
    searches = read("searches")
    for s in searches:
        s["searched_at"] = parse_time(s["searched_at"])
    return posts, apps, searches


def rate(pair):
    """(hits, total) -> hits / total, or None when total is 0."""
    return pair[0] / pair[1] if pair and pair[1] else None


# Your turn.

def post_liquidity(posts, applications, as_of=AS_OF, window_hours=48):
    """{city: (filled, eligible)} plus an ALL key that pools every city."""
    # TODO
    raise NotImplementedError


def search_success(searches, posts):
    """{city: (searches that found an open post, searches)} plus ALL."""
    # TODO
    raise NotImplementedError


def diagnose(liquidity, success, target=0.8):
    """{key: "workers" | "employers" | "both" | "neither" | None} for every key in either input."""
    # TODO
    raise NotImplementedError
