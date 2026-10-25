"""Lesson 03: active users and stickiness. Your turn.

Rules: standard library only (csv, datetime).
Fill in every function marked TODO, then run: python3 test_lesson.py
"""
import csv
import datetime


def active_by_day(path, actions=None):
    """Return {date_text: set of user_ids active that day}.
    actions is a set of event names that count as active; None means any event.
    user_id must be an int."""
    # TODO
    raise NotImplementedError


def window(end_date, days):
    """The list of date texts ('YYYY-MM-DD') in the window of `days` days that ends
    on end_date, inclusive, oldest first. window('2026-09-30', 3) is
    ['2026-09-28', '2026-09-29', '2026-09-30']."""
    # TODO
    raise NotImplementedError


def dau(by_day, date):
    """Distinct active users on one date (0 if nobody was active)."""
    # TODO
    raise NotImplementedError


def active_in_window(by_day, end_date, days):
    """Distinct users active at least once in the `days` days ending on end_date.
    days=7 gives WAU, days=30 gives MAU. A user active on five days counts once."""
    # TODO
    raise NotImplementedError


def stickiness(by_day, end_date, days=30):
    """DAU/MAU: the average DAU over the window (sum of daily DAU / days)
    divided by the distinct active users in the same window. 0.0 if nobody was active."""
    # TODO
    raise NotImplementedError
