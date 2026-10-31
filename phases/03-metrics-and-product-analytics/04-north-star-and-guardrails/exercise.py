"""Lesson 04: north star and guardrails. Your turn.

North star: share of job seekers who send at least one application (applying users).
Guardrail 1: employer reply rate = replies / applications (quality for employers).
Guardrail 2: unsubscribe rate = unsubscribed users / users (harm to job seekers).
Rules: standard library only (csv, math).
Fill in every function marked TODO, then run: python3 test_lesson.py
"""
import csv
import math


def summarize(path):
    """Read the experiment CSV and return, for each variant,
    {"users", "applying_users", "applications", "replies", "unsubscribes"} as ints.
    applying_users = users with applications > 0."""
    # TODO
    raise NotImplementedError


def metrics(s):
    """Return {"north_star", "reply_rate", "unsubscribe_rate", "users", "applications"}
    for one variant summary.
    north_star       = applying_users / users
    reply_rate       = replies / applications
    unsubscribe_rate = unsubscribes / users
    users, applications: copied from the summary (the rule needs them to size the noise).
    Use 0.0 for a rate whose denominator is 0."""
    # TODO
    raise NotImplementedError


def diff_interval(p0, n0, p1, n1, z=1.96):
    """The change p1 - p0 between two proportions and its interval:
    se = sqrt(p0 (1 - p0) / n0 + p1 (1 - p1) / n1), interval = change -/+ z x se.
    Return (change, low, high), or None if either n is 0."""
    # TODO
    raise NotImplementedError


def decide(control, treatment, min_lift=0.02, max_reply_drop=0.02, max_unsub_rise=0.005, z=1.96):
    """The launch rule, written before the test. control and treatment come from metrics().
    All changes are absolute (treatment - control). Use diff_interval for each metric
    (north star and unsubscribe rate over users, reply rate over applications).
    Launch only if
      the north star lift is at least min_lift AND its interval's low end is above 0,
      AND the reply rate interval's low end is no lower than -max_reply_drop,
      AND the unsubscribe rate interval's high end is no higher than +max_unsub_rise.
    A guardrail whose interval is None fails.
    Return {"decision": "launch" or "do not launch",
            "north_star_lift": treatment north star - control north star,
            "intervals": {"north_star": ..., "reply_rate": ..., "unsubscribe_rate": ...}
                         each the (change, low, high) from diff_interval, or None,
            "breaches": sorted list of the guardrail names that failed ("reply_rate", "unsubscribe_rate")}."""
    # TODO
    raise NotImplementedError
