"""Exercise: out of 60 applications, where is your search leaking, and which channel deserves more time?

Fill in the functions marked TODO. Then run: python3 test_lesson.py
"""
import csv
import datetime
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
AS_OF = "2026-10-31"
Z95 = 1.96
STAGES = [("applied_on", "reply_on"), ("reply_on", "interview_on"), ("interview_on", "offer_on")]


def load_applications():
    with open(os.path.join(DATA, "applications.csv"), newline="") as f:
        return list(csv.DictReader(f))


def days_between(a, b):
    return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days


def wilson(k, n, z=Z95):
    """95% Wilson score interval for k successes out of n. (0.0, 1.0) when n is 0."""
    # TODO
    raise NotImplementedError


def stage_counts(apps, from_col, to_col, as_of=AS_OF, wait_days=21):
    """Count one step of the funnel among rows that reached from_col.

    passed:  to_col has a date
    failed:  no to_col, and either a rejection is recorded or wait_days have gone by since from_col
    waiting: no to_col, no rejection, younger than wait_days (right-censored: left out of n)
    Return {"k": passed, "n": passed + failed, "waiting": waiting}.
    """
    # TODO
    raise NotImplementedError


def funnel(apps, as_of=AS_OF, wait_days=21):
    """[(from_col, to_col, counts)] for the three steps: applied to reply, reply to interview,
    interview to offer."""
    # TODO
    raise NotImplementedError


def replied_within(apps, days, as_of=AS_OF):
    """(k, n): among applications at least `days` old, how many had a reply within `days`."""
    # TODO
    raise NotImplementedError


def by_channel(apps, as_of=AS_OF, wait_days=28):
    """Per channel: applications to interviews with censoring, a Wilson interval, mean hours
    per application, and interviews per 10 hours (with the interval scaled the same way).

    Return {channel: {"k", "n", "waiting"} from stage_counts(applied_on -> interview_on), plus
    "apps": applications in the channel, "rate": k / n (None when n is 0), "low" and "high":
    the Wilson interval, "hours": mean hours_spent over ALL the channel's applications,
    "per_10h": rate x 10 / hours (None when n is 0), "low_10h" and "high_10h": low and high
    scaled the same way}.
    """
    # TODO
    raise NotImplementedError


def recommend(stats):
    """Best channel by interviews per 10 hours, and whether the evidence is clear: its lower
    bound is above every other channel's upper bound. None if no channel has a decided row."""
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    A = load_applications()
    for f, t, c in funnel(A):
        print(f, "->", t, c)
    stats = by_channel(A)
    for ch, s in stats.items():
        print(ch, s["k"], s["n"], s["waiting"], round(s["per_10h"], 2))
    print(recommend(stats))
