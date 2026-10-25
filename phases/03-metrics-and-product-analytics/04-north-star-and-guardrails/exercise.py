"""Lesson 04: north star and guardrails. Your turn.

North star: share of job seekers who send at least one application (applying users).
Guardrail 1: employer reply rate = replies / applications (quality for employers).
Guardrail 2: unsubscribe rate = unsubscribed users / users (harm to job seekers).
Rules: standard library only (csv).
Fill in every function marked TODO, then run: python3 test_lesson.py
"""
import csv


def summarize(path):
    """Read the experiment CSV and return, for each variant,
    {"users", "applying_users", "applications", "replies", "unsubscribes"} as ints.
    applying_users = users with applications > 0."""
    # TODO
    raise NotImplementedError


def metrics(s):
    """Return {"north_star", "reply_rate", "unsubscribe_rate"} for one variant summary.
    north_star       = applying_users / users
    reply_rate       = replies / applications
    unsubscribe_rate = unsubscribes / users
    Use 0.0 when a denominator is 0."""
    # TODO
    raise NotImplementedError


def decide(control, treatment, min_lift=0.02, max_reply_drop=0.02, max_unsub_rise=0.005):
    """The launch rule, written before the test. All changes are absolute (treatment - control).
    Launch only if the north star rises by at least min_lift
    AND reply_rate falls by no more than max_reply_drop
    AND unsubscribe_rate rises by no more than max_unsub_rise.
    Return {"decision": "launch" or "do not launch",
            "north_star_lift": treatment north star - control north star,
            "breaches": sorted list of the guardrail names that failed ("reply_rate", "unsubscribe_rate")}."""
    # TODO
    raise NotImplementedError
