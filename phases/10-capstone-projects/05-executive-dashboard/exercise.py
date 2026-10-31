"""Capstone 10-05: the Kettlemoor executive dashboard. Your submission.

Read BRIEF.md (the request and the data notes) and DELIVERABLES.md (what to
hand in and the exact definitions). This file holds the part of the
deliverable with one right answer: the model and the KPI numbers. Fill in
every function, then run `python3 test_lesson.py`. Standard library and
sqlite3 only; the dashboard itself can be drawn in any tool you like.
"""
import csv
import datetime as dt
import os
import sqlite3

REPORT_MONTH = "2026-09"


# ---- given ----------------------------------------------------------------------

def load(folder):
    """The four raw CSVs as {"daily_sales", "stores", "store_closures", "targets"}: lists of dicts of text."""
    out = {}
    for name in ("daily_sales", "stores", "store_closures", "targets"):
        with open(os.path.join(folder, name + ".csv"), newline="") as f:
            out[name] = list(csv.DictReader(f))
    return out


def query(con, sql, params=()):
    """Run sql and return a list of dicts, one per row."""
    cur = con.execute(sql, params)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


def add_months(month, n):
    i = int(month[:4]) * 12 + int(month[5:7]) - 1 + n
    return "%04d-%02d" % (i // 12, i % 12 + 1)


def status(vs_target_pct):
    """green at or above 100% of target, amber from 95% up to 100%, red below 95%, None without a target."""
    if vs_target_pct is None:
        return None
    if vs_target_pct >= 100:
        return "green"
    return "amber" if vs_target_pct >= 95 else "red"


# ---- yours ------------------------------------------------------------------------

def clean_sales(rows):
    """One row per (sales_date, store_id): the load with the latest loaded_at.
    net_revenue = gross_sales - discounts before 2026-07-01, gross_sales from then on.
    Returns dicts with sales_date, store_id, orders (int), net_revenue, cogs (floats),
    sorted by (sales_date, store_id)."""
    # TODO
    raise NotImplementedError


def build_model(raw):
    """An in-memory SQLite star schema:
    dim_date(date_key, month, year, day_of_week 0 = Monday, is_weekend 0/1): every day from
        the first to the last sales_date, with no gaps;
    dim_store(store_id, store_name, city, opened_on);
    store_closure(store_id, closed_from, closed_to);
    fact_sales(date_key, store_id, orders, net_revenue, cogs): one row per day and store, clean;
    fact_target(month, store_id, revenue_target)."""
    # TODO
    raise NotImplementedError


def check_model(con):
    """Tests a dashboard model must pass before anyone sees a number. Returns a list of
    problems (empty when the model is sound), one short sentence each:
    duplicate (date_key, store_id) in fact_sales; a fact_sales date_key not in dim_date;
    a fact_sales or fact_target store_id not in dim_store; a negative orders, net_revenue
    or cogs; sales on a day the store was closed or before it opened; a gap in dim_date."""
    # TODO
    raise NotImplementedError


def missing_days(con, month):
    """(store_id, date_key) pairs in `month` where the store was open (opened, not in a
    closure) but fact_sales has no row: data that never arrived. Sorted."""
    # TODO
    raise NotImplementedError


def lfl_stores(con, month):
    """Like-for-like stores for `month`: opened on or before the first day of the same month a
    year earlier, and with no closure day in either month. Sorted store_ids."""
    # TODO
    raise NotImplementedError


def monthly_kpis(con, month):
    """The CEO cards for `month`. Keys:
    net_revenue, orders, aov (net_revenue / orders), gross_margin_pct (100 x (net_revenue - cogs)
    / net_revenue), target (sum of fact_target), vs_target_pct (100 x net_revenue / target),
    status (from vs_target_pct), net_revenue_ly (same month a year earlier), yoy_pct
    (100 x (net_revenue / net_revenue_ly - 1)), lfl_stores, lfl_growth_pct (the same over
    like-for-like stores only), missing_days (count from missing_days).
    Money and percentages rounded to 2 decimals; a ratio with a zero or missing denominator is None."""
    # TODO
    raise NotImplementedError


def store_table(con, month):
    """One row per store with sales or a target in `month`, sorted by store_id: store_id,
    net_revenue, target, vs_target_pct, status, gross_margin_pct. Same rounding as monthly_kpis."""
    # TODO
    raise NotImplementedError


def trend(con, end_month, n=13):
    """[(month, net_revenue rounded to 2 decimals)] for the n months ending with end_month,
    oldest first; 0.0 for a month with no sales."""
    # TODO
    raise NotImplementedError
