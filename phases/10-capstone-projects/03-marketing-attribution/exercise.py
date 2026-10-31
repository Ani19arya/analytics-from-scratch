"""Capstone 10-03: Brambletoe attribution and next quarter's budget. Your submission.

Read BRIEF.md (the request and the notes from the data team) and DELIVERABLES.md
(what to hand in, with the definitions and the planning steps). This file holds
the part of the deliverable with one right answer: fill in every function, then
run `python3 test_lesson.py`. Standard library only.
"""
import csv
import datetime
import os

Q_START, Q_END = "2026-06-29", "2026-09-27"
TEST_START, TEST_END = "2026-08-03", "2026-08-30"
PAID = ("paid_search", "paid_social", "display")
NO_TOUCH = "(none)"
MODELS = ("first", "last", "linear", "position")
WEEKS_PER_QUARTER = 13

# ---- given ----------------------------------------------------------------


def load(folder):
    """Read the four raw CSVs from `folder`, rows as dicts of text."""
    out = {}
    for name in ("spend", "touchpoints", "orders", "display_test"):
        with open(os.path.join(folder, name + ".csv"), newline="") as f:
            out[name] = list(csv.DictReader(f))
    return out


def parse_time(text):
    """'2026-08-03 14:05' -> datetime."""
    return datetime.datetime.strptime(text, "%Y-%m-%d %H:%M")


def week_start(time_text):
    """The Monday of the week an event falls in, as 'YYYY-MM-DD'."""
    d = datetime.date.fromisoformat(time_text[:10])
    return (d - datetime.timedelta(days=d.weekday())).isoformat()


# ---- yours ----------------------------------------------------------------

def clean_spend(raw_spend):
    """{(week_start, channel): spend as finance counts it}, one value per week and channel."""
    # TODO
    raise NotImplementedError


def clean_orders(raw_orders, start=Q_START, end=Q_END):
    """One row per real order dated start to end inclusive: dicts with order_id, user_id,
    order_time, revenue (int), sorted by order_id."""
    # TODO
    raise NotImplementedError


def attribute(orders, touches, model, lookback_days=30, by_week=False):
    """Credit per channel for `model` in MODELS (keys (week_start, channel) when by_week), adding up
    to len(orders); "(none)" for orders with no touch in the window. ValueError for an unknown model."""
    # TODO
    raise NotImplementedError


def holdout_lift(test_users, orders, start=TEST_START, end=TEST_END, z=1.96):
    """{"n_exposed", "n_holdout", "conv_exposed", "conv_holdout", "lift", "se", "low", "high",
    "incremental"} for the display test; None if a group is empty."""
    # TODO
    raise NotImplementedError


def calibration_factor(test_users, orders, touches, start=TEST_START, end=TEST_END):
    """Incremental display orders in the test / the credit linear attribution gives display on the
    exposed users' test-window orders. None if that credit is 0 or a group is empty."""
    # TODO
    raise NotImplementedError


def fit_sqrt_response(points):
    """a for the curve conversions = a x sqrt(spend), by least squares through the origin.
    points: [(weekly spend, weekly conversions), ...]. None if total spend is 0."""
    # TODO
    raise NotImplementedError


def allocate(a, budget, lower, upper):
    """{channel: spend} that maximises sum of a[c] x sqrt(spend[c]) with the whole budget spent and
    lower[c] <= spend[c] <= upper[c]. ValueError if no such split exists."""
    # TODO
    raise NotImplementedError


def plan(spend, orders, touches, test_users, move=0.5):
    """Next quarter's paid budget by the steps in DELIVERABLES.md. Returns {"calibration", "a",
    "current", "proposed", "current_conversions", "proposed_conversions"}."""
    # TODO
    raise NotImplementedError
