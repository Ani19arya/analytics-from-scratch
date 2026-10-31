"""Lesson 12: unit economics, LTV, CAC and payback. Your turn.

Rules: standard library only (csv).
The definitions are in "The idea" in the README. Fill in every TODO,
then run: python3 test_lesson.py
"""
import csv

MARGIN = 0.70        # gross margin from finance: after app store fees, hosting and support
AS_OF = "2026-10"    # the last month with payments


def next_month(month):
    """'2026-12' -> '2027-01'."""
    y, m = int(month[:4]), int(month[5:])
    return "%04d-%02d" % (y + (m == 12), m % 12 + 1)


def months_between(first, last):
    """Whole months from first to last: ('2026-01', '2026-03') -> 2."""
    # TODO
    raise NotImplementedError


def load(folder):
    """(customers, payments, spend):
    {customer_id: (signup_month, channel)}, {customer_id: {month: amount}}, {channel: total spend}."""
    # TODO
    raise NotImplementedError


def cac(spend, customers, channel):
    """Spend per new customer for the channel, or None with no customers."""
    # TODO
    raise NotImplementedError


def arpu_and_churn(customers, payments, channel, as_of=AS_OF):
    """(ARPU, monthly churn) for the channel; None for either one that cannot be computed."""
    # TODO
    raise NotImplementedError


def margin_ltv(arpu, churn, margin=MARGIN):
    """Margin LTV, or None when it cannot be computed."""
    # TODO
    raise NotImplementedError


def margin_curve(customers, payments, channel, margin=MARGIN, as_of=AS_OF):
    """{n: average margin per customer from their first n months}, eligible customers only."""
    # TODO
    raise NotImplementedError


def payback_months(curve, cac_value):
    """The first n where the curve reaches CAC, or None."""
    # TODO
    raise NotImplementedError
