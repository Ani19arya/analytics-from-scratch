"""Lesson 11: attribution models. Your turn.

Rules: standard library only (csv, datetime).
The rules (lookback window, tie order, the four models) are in "The idea" in the
README. Fill in every TODO, then run: python3 test_lesson.py
"""
import csv
import datetime

LOOKBACK_DAYS = 30
NO_TOUCH = "(none)"
MODELS = ("first", "last", "linear", "time_decay")


def parse_time(text):
    """'2026-10-01 14:05' -> datetime."""
    # TODO
    raise NotImplementedError


def load(touch_path, conv_path, lookback_days=LOOKBACK_DAYS):
    """[{"user_id", "time", "revenue", "path": [(time, channel), ...]}, ...], oldest purchase first."""
    # TODO
    raise NotImplementedError


def weights(path, model, conv_time, half_life_days=7.0):
    """{channel: share of this purchase}, adding up to 1. ValueError for an unknown model."""
    # TODO
    raise NotImplementedError


def attribute(purchases, model, value="count", half_life_days=7.0):
    """{channel: credit}; value is "count" (purchases) or "revenue"."""
    # TODO
    raise NotImplementedError


def spread(purchases, models=MODELS):
    """{channel: (lowest credit, highest credit)} across the models."""
    # TODO
    raise NotImplementedError
