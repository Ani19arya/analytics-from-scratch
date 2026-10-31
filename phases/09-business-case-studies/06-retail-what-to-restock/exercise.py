"""Case 06: retail, what to restock. Your turn.

Steps 7 to 9 of the case: two SQL queries (SQLite) and the Python that turns
them into a restock plan. Sales cover 12 weeks from Monday 3 August 2026; the
plan is for the 4 weeks of November.
"""
import csv
import math
import os
import sqlite3

HORIZON_WEEKS = 4      # the plan covers the next 4 weeks
MAX_COVER_WEEKS = 12   # stock beyond 12 weeks of demand is "tying up cash"

# ---- given: loading the CSVs into SQLite ---------------------------------

def load_db(products_path, sales_path):
    """Load both CSVs into an in-memory SQLite database (tables products and weekly_sales)."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE products (sku TEXT, name TEXT, category TEXT, unit_cost REAL,"
                " unit_price REAL, on_hand INTEGER, lead_time_weeks INTEGER)")
    con.execute("CREATE TABLE weekly_sales (week_start TEXT, sku TEXT, units_sold INTEGER, in_stock INTEGER)")
    with open(products_path, newline="") as f:
        con.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)",
                        [[r["sku"], r["name"], r["category"], float(r["unit_cost"]), float(r["unit_price"]),
                          int(r["on_hand"]), int(r["lead_time_weeks"])] for r in csv.DictReader(f)])
    with open(sales_path, newline="") as f:
        con.executemany("INSERT INTO weekly_sales VALUES (?, ?, ?, ?)",
                        [[r["week_start"], r["sku"], int(r["units_sold"]), int(r["in_stock"])]
                         for r in csv.DictReader(f)])
    return con


def query(con, sql):
    """Run sql and return a list of dicts, one per row."""
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


# ---- step 7: SQL ---------------------------------------------------------

# SKU_SQL: one row per product in products.csv, including products with no
# sales rows. Columns: sku, category, unit_cost, unit_price, on_hand,
# lead_time_weeks, weeks (sales rows), in_stock_weeks, units_in_stock (units
# sold in weeks with in_stock = 1), units_total. Counts are 0, never NULL.
# Order by sku.
SKU_SQL = """
-- TODO: your query here
"""

# WEEKLY_SQL: one row per week_start. Columns: week_start, units (all units
# sold), revenue (units x unit_price, rounded to 2 decimals), skus_out
# (products with in_stock = 0 that week). Order by week_start.
WEEKLY_SQL = """
-- TODO: your query here
"""


# ---- step 7 and 9: Python ------------------------------------------------

def demand_per_week(row):
    """Units a week customers wanted: units sold in in-stock weeks divided by
    the number of in-stock weeks. None when there is no in-stock week (we
    cannot tell what demand is)."""
    # TODO
    raise NotImplementedError


def plan(sku_rows, horizon=HORIZON_WEEKS, max_cover=MAX_COVER_WEEKS):
    """One dict per SKU, in the order given, with:
    sku, category, demand (per week or None), cover_weeks (on_hand / demand,
    None when demand is None or 0), order_qty (whole units: demand x (lead time
    + horizon) minus on_hand, rounded up, never below 0), order_cost
    (order_qty x unit_cost), excess_units (on_hand above max_cover weeks of
    demand, never below 0), excess_value (excess_units x unit_cost),
    lost_margin (units customers wanted in out-of-stock weeks but could not buy,
    x (unit_price - unit_cost), never below 0) and action:
    'review' when demand is None, else 'restock' when order_qty > 0, else
    'overstock' when excess_units > 0, else 'hold'.
    When demand is None, order_qty, order_cost, excess_units, excess_value and
    lost_margin are 0."""
    # TODO
    raise NotImplementedError


def summarise(plan_rows):
    """Totals for the decision: a dict with counts per action (keys 'restock',
    'overstock', 'hold', 'review', all present even when 0), order_cost (total
    cash the restock needs), cash_tied_up (total excess_value) and lost_margin
    (total)."""
    # TODO
    raise NotImplementedError


# ---- step 8: a chart you can paste into a message ------------------------

def text_chart(items, width=30):
    """items: (label, value) pairs with value >= 0. One line per item:
    the label padded to the longest label, the value with no decimals, then a
    bar of '#'. The largest value gets `width` characters; others are scaled
    and rounded. All values 0: no bars."""
    # TODO
    raise NotImplementedError
