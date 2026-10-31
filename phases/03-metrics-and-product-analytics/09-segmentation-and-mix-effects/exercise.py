"""Lesson 09: segmentation and mix effects. Your turn.

Rules: standard library only (csv).
The formulas are in "The idea" in the README. Fill in every TODO,
then run: python3 test_lesson.py
"""
import csv


def load_periods(path, split_date):
    """Return {"prior": {segment: [sessions, orders]}, "current": {...}}."""
    # TODO
    raise NotImplementedError


def overall_rate(period):
    """Total orders / total sessions, or None with no sessions."""
    # TODO
    raise NotImplementedError


def decompose(prior, current):
    """Return {"total", "mix", "rate", "segments": {segment: {"w0", "w1", "r0", "r1", "mix", "rate"}}},
    or None if either period has no sessions. mix + rate must equal total exactly.
    Decide how to handle a segment that has no sessions in one of the periods."""
    # TODO
    raise NotImplementedError


def main_cause(result):
    """"mix" or "rate", whichever is larger in absolute size. A tie goes to "rate"."""
    # TODO
    raise NotImplementedError
