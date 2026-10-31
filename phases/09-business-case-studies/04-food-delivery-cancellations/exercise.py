"""Case 04: food delivery, why are cancellations rising? Your turn.

Steps 7 to 9 of the case: three SQL queries (SQLite) and the Python that turns
them into an answer. Weeks run Monday to Sunday from 3 August 2026; weeks 1 to 6
are "before" and weeks 7 to 12 are "after".
"""
import csv
import os
import sqlite3

START = "2026-08-03"

# ---- given: loading the CSV into SQLite ----------------------------------

def load_db(path):
    """Load orders.csv into an in-memory SQLite table called orders.
    A blank cancel_reason becomes NULL, as it would in a warehouse."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE orders (order_id TEXT, order_date TEXT, city TEXT, restaurant_id TEXT,"
                " app_version TEXT, status TEXT, cancel_reason TEXT)")
    with open(path, newline="") as f:
        rows = [[r[k] or None for k in ("order_id", "order_date", "city", "restaurant_id",
                                          "app_version", "status", "cancel_reason")]
                for r in csv.DictReader(f)]
    con.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    return con


def query(con, sql):
    """Run sql and return a list of dicts, one per row."""
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


# ---- step 7: SQL ---------------------------------------------------------

# WEEKLY_SQL: one row per week. Columns: week (1 to 12, week 1 starts Monday
# 3 August 2026), orders, cancelled, cancel_rate_pct (rounded to 1 decimal).
# Order by week.
WEEKLY_SQL = """
-- TODO: your query here
"""

# REASON_SQL: cancellations by period and cancel_reason. period is 'before'
# (weeks 1 to 6) or 'after' (weeks 7 to 12). Columns: period, cancel_reason,
# cancelled, per_100_orders = 100 x cancelled / ALL orders in that period,
# rounded to 2 decimals. Only reasons that occur; order by period, cancel_reason.
REASON_SQL = """
-- TODO: your query here
"""

# SEGMENT_SQL: columns city, app_version, period, orders, cancelled.
# Order by city, app_version, period.
SEGMENT_SQL = """
-- TODO: your query here
"""


# ---- step 7 and 9: Python ------------------------------------------------

def excess_by_segment(segments):
    """segments: rows of SEGMENT_SQL. For each (city, app_version) in the after
    period, expected = after orders x the city's before cancel rate (all versions
    together). A city with no before orders uses the overall before rate.
    Return dicts {city, app_version, orders, cancelled, expected, excess},
    sorted by excess, largest first; ties by city then app_version."""
    # TODO
    raise NotImplementedError


def top_segment_share(excess_rows):
    """The first row's excess divided by the total excess of all rows.
    It can be above 1 when other segments got better. None when there are
    no rows or the total excess is not positive."""
    # TODO
    raise NotImplementedError


def rate_without(segments, city, app_version):
    """The after-period cancel rate in percent with one (city, app_version)
    segment taken out: what the business would look like without it.
    None when no after orders are left."""
    # TODO
    raise NotImplementedError


# ---- step 8: a chart you can paste into a message ------------------------

def text_chart(weekly, width=30):
    """One line per week: 'W01   4.7% ####'. The longest bar (the highest
    rate) has `width` characters; the others are scaled and rounded."""
    # TODO
    raise NotImplementedError
