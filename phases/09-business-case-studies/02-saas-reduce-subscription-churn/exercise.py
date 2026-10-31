"""Case 02: SaaS, reduce subscription churn. Your turn.

Steps 7 to 9 of the case: two SQL queries (SQLite) and the Python that turns
them into an answer. The data is observed at the end of October 2026
(AS_OF). A customer's tenure is counted in whole months from the signup
month: to the churn month if they left, to AS_OF if they are still active.
"""
import csv
import os
import sqlite3

AS_OF = "2026-10"

# ---- given: loading the CSV into SQLite ----------------------------------


def load_db(path):
    """Load customers.csv into an in-memory SQLite table called customers.
    A blank churn_month (still active) becomes NULL."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE customers (customer_id TEXT, signup_month TEXT, plan TEXT, seats INTEGER,"
                " mrr INTEGER, onboarded TEXT, churn_month TEXT)")
    with open(path, newline="") as f:
        rows = [(r["customer_id"], r["signup_month"], r["plan"], int(r["seats"]), int(r["mrr"]),
                 r["onboarded"], r["churn_month"] or None) for r in csv.DictReader(f)]
    con.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    return con


def query(con, sql):
    """Run sql and return a list of dicts, one per row."""
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


# ---- step 7: SQL ---------------------------------------------------------

# LIFE_SQL: a life table per plan. One row per plan and tenure month n, from 1
# to the longest tenure in the data. Columns: plan, tenure_month,
# at_risk (customers whose tenure is n or more: still subscribed at the start
# of month n), churned (customers who left with tenure exactly n),
# hazard_pct = 100 x churned / at_risk rounded to 2 decimals (NULL when
# at_risk is 0). Tenure = months from signup_month to churn_month, or to
# '2026-10' for active customers. Order by plan, tenure_month.
LIFE_SQL = """
-- TODO: your query here
"""

# SEGMENT_SQL: one row per plan, onboarded and size. size is '1-2' for 1 or
# 2 seats, '3+' otherwise. Columns: plan, onboarded, size, customers,
# churned, customer_months (the sum of every customer's tenure, as above),
# active_customers, active_mrr (MRR of customers still active),
# churned_mrr (MRR of customers who left). Order by plan, onboarded, size.
SEGMENT_SQL = """
-- TODO: your query here
"""


# ---- step 7 and 9: Python ------------------------------------------------

def survival(life_rows, plan):
    """The share of a plan's customers still subscribed after each tenure month:
    S(n) = product over months 1..n of (1 - churned / at_risk).
    Return [(tenure_month, survival), ...] in order, stopping before the first
    month with nobody at risk. [] when the plan has no rows."""
    # TODO
    raise NotImplementedError


def monthly_hazard(segment):
    """Churned / customer_months: the chance a customer leaves in any one
    month they are subscribed. None when customer_months is 0."""
    # TODO
    raise NotImplementedError


def lever(segments, field, from_value, to_value):
    """What changing customers from `from_value` to `to_value` on `field`
    (for example onboarded 'no' to 'yes') would keep, per month, if their
    monthly hazard fell to that of the matching segment (same values on the
    other two of plan, onboarded, size) with `to_value`.
    For each matched pair: kept = active x max(0, hazard from - hazard to),
    for MRR (active_mrr) and for customers (active_customers).
    Pairs where either hazard is None, or with no match, are skipped.
    Return {"mrr_kept": ..., "customers_kept": ...}."""
    # TODO
    raise NotImplementedError


def churn_shares(segments, field):
    """For each value of `field`, its share of all churned customers and of
    all churned MRR, as fractions: {value: {"customers": ..., "mrr": ...}}.
    A share is None when nobody churned at all."""
    # TODO
    raise NotImplementedError


# ---- step 8: a chart you can paste into a message ------------------------

def text_chart(points, width=30):
    """points: [(label, fraction between 0 and 1), ...]. One line per point:
    the label padded to 10, the percent with 1 decimal in 6 characters, then a
    bar of round(fraction x width) '#' characters (the scale is fixed: 100%
    is `width`, so curves on different charts compare)."""
    # TODO
    raise NotImplementedError

