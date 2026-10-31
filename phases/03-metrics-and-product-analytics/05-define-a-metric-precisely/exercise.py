"""Lesson 05: define a metric precisely. Your turn.

The definition finance agreed, in words:
  "A monthly active customer is a real customer (not a staff test account) with at
   least one DELIVERED order placed in that calendar month, India time, that was not
   refunded in full. Customers who later deleted their account, or had their data
   erased, still count for the months they were active."

Step 1: fill in SPEC so each value says exactly what the sentence says.
Step 2: fill in every function marked TODO, then run: python3 test_lesson.py
Rules: standard library only (csv, datetime).
"""
import csv
import datetime

SPEC = {
    "name": "monthly_active_customers",
    "counts": "distinct customer_id",
    "utc_offset_minutes": None,      # TODO: India Standard Time is UTC+05:30. How many minutes is that?
    "statuses": None,                # TODO: a list of the order statuses that count
    "exclude_full_refunds": None,    # TODO: True or False
    "exclude_test_accounts": None,   # TODO: True or False
    "keep_deleted_customers": None,  # TODO: True or False
}

# What the growth dashboard has been counting: any order created in the UTC month.
# Given, not a TODO. Your functions must work for this spec too.
DASHBOARD_SPEC = {
    "name": "customers_with_any_order_utc",
    "counts": "distinct customer_id",
    "utc_offset_minutes": 0,
    "statuses": ["delivered", "cancelled"],
    "exclude_full_refunds": False,
    "exclude_test_accounts": False,
    "keep_deleted_customers": True,
}


def parse_utc(text):
    """'2026-10-01T18:45:00Z' -> an aware datetime in UTC.
    Hint: datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    (Python 3.9's fromisoformat does not accept the trailing Z.)"""
    # TODO
    raise NotImplementedError


def local_month(created_at, offset_minutes):
    """The 'YYYY-MM' an order created at `created_at` (UTC text) falls in, on a clock
    that is offset_minutes ahead of UTC. '2026-09-30T18:45:00Z' is '2026-10' in India
    (offset 330) and '2026-09' in UTC (offset 0)."""
    # TODO
    raise NotImplementedError


def read_customers(path):
    """{customer_id (int): {"customer_id": int, "email": str, "is_test": int,
    "deleted_at": the text, or None when the cell is blank}}"""
    # TODO
    raise NotImplementedError


def read_orders(path):
    """A list of dicts: order_id and customer_id as int, created_at and status as text,
    amount and refunded_amount as float. A blank refunded_amount means no refund: 0.0."""
    # TODO
    raise NotImplementedError


def is_full_refund(order):
    """True when refunded_amount is more than 0 AND at least the amount.
    A free meal (amount 0, refunded 0) was not refunded."""
    # TODO
    raise NotImplementedError


def qualifies(order, customer, spec):
    """Does this order make its customer active under `spec`? Ignore the month here.
    customer is the customers row for the order's customer_id, or None when the row
    was erased. An erased customer is a real customer, not a test account.
    Check, in any order: status is in spec["statuses"]; if spec["exclude_full_refunds"],
    not a full refund; if spec["exclude_test_accounts"], not is_test; if not
    spec["keep_deleted_customers"], the customer row exists and deleted_at is None."""
    # TODO
    raise NotImplementedError


def active_customers(orders, customers, month, spec):
    """The SET of distinct customer_ids with at least one qualifying order whose
    local_month(created_at, spec["utc_offset_minutes"]) equals `month` ('YYYY-MM')."""
    # TODO
    raise NotImplementedError


def reconcile(orders, customers, month, steps):
    """steps is a list of (label, spec). Return a list of (label, count of active
    customers under that spec), in the same order."""
    # TODO
    raise NotImplementedError


def bridge_steps():
    """From the dashboard definition to SPEC, changing one rule at a time. Given."""
    steps = [("dashboard: any order, UTC month", dict(DASHBOARD_SPEC))]
    current = dict(DASHBOARD_SPEC)
    for label, key in (("+ India time month", "utc_offset_minutes"), ("+ delivered only", "statuses"),
                       ("+ no full refunds", "exclude_full_refunds"), ("+ no test accounts", "exclude_test_accounts")):
        current = dict(current)
        current[key] = SPEC[key]
        steps.append((label, current))
    return steps
