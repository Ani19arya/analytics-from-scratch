"""Lesson 07: growth accounting. Your turn.

MAU this month = MAU last month + new + resurrected - churned
Rules: standard library only (csv).
Fill in every function marked TODO, then run: python3 test_lesson.py
"""
import csv


def load_activity(path):
    """Return {user_id: set of 'YYYY-MM' months with at least one session}.
    Decide what to do with a blank user_id (the test expects it to be skipped)."""
    # TODO
    raise NotImplementedError


def prev_month(month):
    """'2026-01' -> '2025-12'."""
    # TODO
    raise NotImplementedError


def month_range(first, last):
    """Every calendar month from first to last inclusive."""
    # TODO
    raise NotImplementedError


def account(activity, month):
    """Return {"month", "mau", "prev_mau", "new", "retained", "resurrected", "churned"}.
    Read the definitions in the README carefully: new and resurrected are not the same thing."""
    # TODO
    raise NotImplementedError


def growth_table(activity):
    """One account() row per calendar month, first to last month in the data, gaps included."""
    # TODO
    raise NotImplementedError


def quick_ratio(row):
    """(new + resurrected) / churned, or None when nobody churned."""
    # TODO
    raise NotImplementedError
