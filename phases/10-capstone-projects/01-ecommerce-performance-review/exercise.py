"""Capstone 10-01: Pottlemere quarterly business review. Your submission.

Read BRIEF.md (the request and the notes from the data team) and DELIVERABLES.md
(what to hand in). This file holds the part of the deliverable with one right
answer: fill in every function, then run `python3 test_lesson.py`.
Standard library only. Keep amounts as floats: do not round per row.
"""
import csv
import os

# ---- given ----------------------------------------------------------------


def load(folder):
    """Read the three raw CSVs from `folder`: {"orders", "refunds", "customers"}, rows as dicts of text."""
    out = {}
    for name in ("orders", "refunds", "customers"):
        with open(os.path.join(folder, name + ".csv"), newline="") as f:
            out[name] = list(csv.DictReader(f))
    return out


def quarter_of(date_text):
    """'2026-08-14' -> '2026-Q3'."""
    return "%s-Q%d" % (date_text[:4], (int(date_text[5:7]) - 1) // 3 + 1)


# ---- yours ----------------------------------------------------------------

def clean_orders(raw_orders, as_of=None):
    """One row per order as the warehouse knew it on `as_of` (a 'YYYY-MM-DD' load date; None = every row).
    Only orders that count as sales. Returns dicts with order_id, customer_id, order_date and
    net_amount (excluding tax, a float), sorted by order_id."""
    # TODO
    raise NotImplementedError


def clean_refunds(raw_refunds, as_of=None):
    """One row per refund as known on `as_of`. Returns dicts with refund_id, order_id, refund_date
    and refund_amount (a float), sorted by refund_id."""
    # TODO
    raise NotImplementedError


def quarter_summary(orders, refunds, quarter):
    """The QBR numbers for one quarter ('2026-Q3') from CLEAN orders and refunds, using the
    definitions in DELIVERABLES.md. Returns {"quarter", "orders", "customers", "new_customers",
    "returning_customers", "net_sales", "refunds", "net_revenue", "aov"}; aov is None with no orders."""
    # TODO
    raise NotImplementedError


def restate(raw_orders, raw_refunds, quarter, reported_as_of):
    """Net revenue for `quarter` as reported on `reported_as_of` and as known now.
    Returns {"reported", "restated", "change"}, change = restated - reported."""
    # TODO
    raise NotImplementedError


def new_customers_by_channel(orders, customers, quarter):
    """{acquisition_channel: new customers in `quarter`}, from clean orders and the raw customers rows.
    A customer missing from the customers table counts under "unknown"."""
    # TODO
    raise NotImplementedError


def mean_diff_ci(a, b, z=1.96):
    """mean(b) - mean(a) with a Welch (unequal variances) normal interval.
    Returns {"diff", "se", "low", "high"}; None when either list has fewer than 2 values."""
    # TODO
    raise NotImplementedError


def monthly_net_sales(orders):
    """{'YYYY-MM': net sales} from clean orders, months in order."""
    # TODO
    raise NotImplementedError
