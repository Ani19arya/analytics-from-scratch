"""Case 03: marketing, is the campaign incremental? Your turn.

Steps 7 to 9 of the case: one SQL query (SQLite) and the Python that turns it
into an answer. The campaign ran 1 to 28 September 2026 ('campaign' period);
4 to 31 August 2026 is the 'pre' period. In every segment a random 10% of
customers (grp 'holdout') got no campaign messages.
"""
import csv
import math
import os
import sqlite3

# ---- given: loading the CSVs into SQLite ---------------------------------


def load_db(folder):
    """Load audience.csv and daily.csv from `folder` into an in-memory SQLite database."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE audience (segment TEXT, grp TEXT, customers INTEGER)")
    con.execute("CREATE TABLE daily (date TEXT, segment TEXT, grp TEXT, orders INTEGER, code_orders INTEGER,"
                " revenue INTEGER, code_revenue INTEGER)")
    with open(os.path.join(folder, "audience.csv"), newline="") as f:
        con.executemany("INSERT INTO audience VALUES (?, ?, ?)",
                        [(r["segment"], r["grp"], int(r["customers"])) for r in csv.DictReader(f)])
    with open(os.path.join(folder, "daily.csv"), newline="") as f:
        con.executemany("INSERT INTO daily VALUES (?, ?, ?, ?, ?, ?, ?)",
                        [(r["date"], r["segment"], r["grp"], int(r["orders"]), int(r["code_orders"]),
                          int(r["revenue"]), int(r["code_revenue"])) for r in csv.DictReader(f)])
    return con


def query(con, sql):
    """Run sql and return a list of dicts, one per row."""
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


# ---- step 7: SQL ---------------------------------------------------------

# GROUP_SQL: one row per period, segment and grp in the audience. period is
# 'campaign' for dates from 2026-09-01 and 'pre' before that. Columns:
# period, segment, grp, customers (from audience), orders, code_orders,
# revenue, code_revenue (0, not NULL, for a group with no daily rows in a
# period). Every audience group appears in both periods.
# Order by period, segment, grp.
GROUP_SQL = """
-- TODO: your query here
"""


# ---- step 7 and 9: Python ------------------------------------------------

def lift(rows, segment, period="campaign", z=1.96):
    """The campaign's incremental orders in one segment, from rows of GROUP_SQL.
    rate = orders / customers for each grp. incremental = (rate campaign -
    rate holdout) x campaign customers. Treat each group's orders as Poisson,
    so se = campaign customers x sqrt(orders_c / n_c^2 + orders_h / n_h^2);
    low and high = incremental -+ z x se.
    incremental_revenue = (revenue per customer campaign - holdout) x campaign customers.
    attributed = the campaign group's code_orders.
    Return {"segment", "rate_campaign", "rate_holdout", "incremental", "se", "low",
    "high", "incremental_revenue", "attributed", "code_revenue"}.
    None if either group is missing or has 0 customers."""
    # TODO
    raise NotImplementedError


def total_lift(rows, period="campaign", z=1.96):
    """Add up lift() over every segment in rows (segments in alphabetical
    order; segments where lift is None are skipped). incremental,
    incremental_revenue, attributed and code_revenue are sums; se is the
    square root of the sum of squared se; low and high use the total se.
    Return the same keys as lift() except the rates, with segment 'all'."""
    # TODO
    raise NotImplementedError


def campaign_profit(rows, segment, margin, discount, period="campaign"):
    """Extra gross profit the campaign made in a segment, from rows of GROUP_SQL.
    Revenue is after discounts; the cost of the goods is (1 - margin) of the
    list price. A code order's list price is its revenue / (1 - discount), so
    a group's gross profit = margin x revenue - (1 - margin) x code_revenue x discount / (1 - discount).
    Return (profit per customer campaign - profit per customer holdout) x
    campaign customers. None when lift() would be None."""
    # TODO
    raise NotImplementedError


# ---- step 8: a chart you can paste into a message ------------------------

def text_chart(lifts, width=30):
    """lifts: results of lift(). Two lines per segment:
    '<segment padded to 8> credited <attributed, 6 wide> <bar of #>' and
    '<8 spaces> real     <incremental rounded, 6 wide> <bar of #>'.
    The largest number across all lines gets `width` characters; a negative
    incremental gets no bar."""
    # TODO
    raise NotImplementedError

