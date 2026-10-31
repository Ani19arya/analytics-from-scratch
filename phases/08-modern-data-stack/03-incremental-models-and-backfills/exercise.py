"""Incremental models and backfills: rebuild only the days that can have changed.

Exercise. The helpers at the top are done for you. Write the six functions
marked TODO, then run: python3 test_lesson.py

Python 3.9+ standard library only. The warehouse is SQLite.

The model is daily_revenue, one row per order_date:
  order_date        'YYYY-MM-DD'
  orders            orders placed that day, any status (latest version of each)
  delivered_orders  of those, how many are delivered now
  revenue           sum of amount over delivered orders, rounded to 2, 0 (not NULL) when none
raw_orders(load_date, order_id, order_date, status, amount) has one row per
order per version; the version with the latest load_date wins. A run on day R
can only see rows with load_date <= R.
"""
import csv
import datetime
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
COLUMNS = ["load_date", "order_id", "order_date", "status", "amount"]


# Given helpers.

def read_raw(data_dir=DATA):
    with open(os.path.join(data_dir, "raw_orders.csv"), newline="") as f:
        return list(csv.DictReader(f))


def load_raw(con, rows=None):
    """Create raw_orders and insert the rows exactly as they landed."""
    rows = read_raw() if rows is None else rows
    con.execute("DROP TABLE IF EXISTS raw_orders")
    con.execute("CREATE TABLE raw_orders (load_date TEXT, order_id INTEGER, order_date TEXT, status TEXT, amount TEXT)")
    con.executemany("INSERT INTO raw_orders VALUES (?, ?, ?, ?, ?)", [[r[c] for c in COLUMNS] for r in rows])
    return con


def shift(day, days):
    """shift('2026-10-01', -3) == '2026-09-28'."""
    return (datetime.date.fromisoformat(day) + datetime.timedelta(days=days)).isoformat()


def table_rows(con):
    """{order_date: (orders, delivered_orders, revenue)} from daily_revenue, or {} when it does not exist."""
    if not con.execute("SELECT 1 FROM sqlite_master WHERE name = 'daily_revenue'").fetchone():
        return {}
    return {r[0]: (r[1], r[2], r[3]) for r in
            con.execute("SELECT order_date, orders, delivered_orders, revenue FROM daily_revenue")}


# The model. Your turn.

CREATE = """CREATE TABLE IF NOT EXISTS daily_revenue (
  order_date TEXT PRIMARY KEY, orders INTEGER, delivered_orders INTEGER, revenue REAL)"""


def build_days(con, lo, hi, as_of):
    """Rewrite daily_revenue for every order_date from lo to hi (both included),
    from the raw rows that had landed by as_of. Create the table if it is not
    there. Leave every other day untouched. Return how many day rows were written.
    """
    raise NotImplementedError("TODO: build_days")


def full_rebuild(con, as_of):
    """Throw daily_revenue away and build every day from scratch, as the data stood on as_of."""
    raise NotImplementedError("TODO: full_rebuild")


def incremental_run(con, run_date, lookback_days):
    """The nightly run on run_date: rewrite the window of days run_date - lookback_days
    to run_date, both included, with what had landed by run_date."""
    raise NotImplementedError("TODO: incremental_run")


def backfill(con, start, end, as_of):
    """Rewrite the days start .. end with everything that had landed by as_of."""
    raise NotImplementedError("TODO: backfill")


def required_lookback(con):
    """The smallest lookback_days that would have caught every row in raw_orders (0 when empty)."""
    raise NotImplementedError("TODO: required_lookback")


def stale_days(con_a, con_b):
    """Sorted order_dates where daily_revenue differs between two databases.
    A day that is in one table and not the other counts as different."""
    raise NotImplementedError("TODO: stale_days")
