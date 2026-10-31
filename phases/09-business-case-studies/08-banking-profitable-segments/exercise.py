"""Case 08: banking, which segments are profitable? Your turn.

Steps 7 to 9 of the case: two SQL queries (SQLite) and the Python that turns
them into an answer. One row per customer for October 2025 to September 2026;
the rates table is an example rate card (fictional).
"""
import csv
import os
import sqlite3

# ---- given: loading the CSVs into SQLite ---------------------------------

def load_db(customers_path, rates_path):
    """Load both CSVs into an in-memory SQLite database (tables customers and rates)."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE customers (customer_id TEXT, segment TEXT, deposit_balance REAL,"
                " loan_balance REAL, fee_income REAL, branch_visits INTEGER, calls INTEGER,"
                " digital_sessions INTEGER, charge_off REAL)")
    con.execute("CREATE TABLE rates (item TEXT, value REAL)")
    with open(customers_path, newline="") as f:
        con.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        [[r["customer_id"], r["segment"], float(r["deposit_balance"]), float(r["loan_balance"]),
                          float(r["fee_income"]), int(r["branch_visits"]), int(r["calls"]),
                          int(r["digital_sessions"]), float(r["charge_off"])] for r in csv.DictReader(f)])
    with open(rates_path, newline="") as f:
        con.executemany("INSERT INTO rates VALUES (?, ?)",
                        [[r["item"], float(r["value"])] for r in csv.DictReader(f)])
    return con


def query(con, sql):
    """Run sql and return a list of dicts, one per row."""
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


# ---- step 7: SQL ---------------------------------------------------------

# PROFIT_SQL: one row per customer. Columns: customer_id, segment,
# revenue = deposit_balance x deposit_margin + loan_balance x loan_margin + fee_income,
# cost_to_serve = branch_visits x branch_visit + calls x call
#                 + digital_sessions x digital_session + account_fixed,
# charge_off, profit = revenue - cost_to_serve - charge_off.
# The rates come from the rates table (one row per item), not typed in.
# Money columns rounded to 2 decimals. Order by customer_id.
PROFIT_SQL = """
-- TODO: your query here
"""

# SEGMENT_SQL: one row per segment. Columns: segment, customers, revenue,
# cost_to_serve, charge_offs, profit, profit_per_customer, unprofitable
# (customers with profit below 0). Money rounded to 2 decimals, computed from
# unrounded customer values. Order by profit, largest first.
SEGMENT_SQL = """
-- TODO: your query here
"""


# ---- step 7 and 9: Python ------------------------------------------------

def even_allocation(segment_rows):
    """The shortcut many banks start with: split the total cost_to_serve
    equally per customer. Return {segment: revenue - charge_offs - customers x
    (total cost_to_serve / total customers)}. Empty input: {}."""
    # TODO
    raise NotImplementedError


def flips(segment_rows):
    """Segments where the two methods disagree on the sign: profitable
    (profit >= 0) under one and loss-making under the other. Sorted by name."""
    # TODO
    raise NotImplementedError


def top_share(profits, fraction):
    """Share of total profit earned by the most profitable `fraction` of
    customers: sort descending, take the first int(len(profits) x fraction)
    customers, divide their profit by the total. None when there are no
    customers or the total profit is not positive."""
    # TODO
    raise NotImplementedError


def whale_curve(profits):
    """The whale curve: cumulative profit with customers sorted from most to
    least profitable. Return a dict: total, peak (the highest cumulative
    profit), peak_ratio (peak / total, None when total is not positive),
    unprofitable (customers with profit below 0)."""
    # TODO
    raise NotImplementedError


# ---- step 8: a chart you can paste into a message ------------------------

def text_chart(items, width=20):
    """items: (label, value) pairs; values can be negative. One line per item:
    the label padded to the longest label, the value with no decimals, then a
    bar: '#' for a positive value, '-' for a negative one. The largest absolute
    value gets `width` characters; others are scaled and rounded."""
    # TODO
    raise NotImplementedError
