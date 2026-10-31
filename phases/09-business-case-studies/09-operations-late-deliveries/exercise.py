"""Case 09: operations, why are deliveries late? Your turn.

Steps 7 to 9 of the case: three SQL queries (SQLite) and the Python that turns
them into an answer. Weeks run Monday to Sunday from 6 July 2026, by order
date; weeks 1 to 6 are "before" and weeks 7 to 12 are "after".
"""
import csv
import datetime
import os
import sqlite3

START = datetime.date(2026, 7, 6)

# ---- given: loading the CSV into SQLite ----------------------------------

def load_db(path):
    """Load shipments.csv into an in-memory SQLite table called shipments."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE shipments (shipment_id TEXT, order_ts TEXT, warehouse TEXT, carrier TEXT,"
                " zone INTEGER, packed_ts TEXT, collected_ts TEXT, delivered_ts TEXT, promised_date TEXT)")
    with open(path, newline="") as f:
        con.executemany("INSERT INTO shipments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        [[r["shipment_id"], r["order_ts"], r["warehouse"], r["carrier"], int(r["zone"]),
                          r["packed_ts"], r["collected_ts"], r["delivered_ts"], r["promised_date"]]
                         for r in csv.DictReader(f)])
    return con


def query(con, sql):
    """Run sql and return a list of dicts, one per row."""
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


# ---- step 7: SQL ---------------------------------------------------------

# WEEKLY_SQL: one row per week of the order date (week 1 starts Monday 6 July
# 2026). Columns: week, shipments, on_time (delivered on or before the
# promised date), on_time_pct (rounded to 1 decimal). Order by week.
WEEKLY_SQL = """
-- TODO: your query here
"""

# STAGE_SQL: one row per warehouse and period ('before' = weeks 1 to 6,
# 'after' = weeks 7 to 12). Columns: warehouse, period, shipments, and the
# average hours of each stage, rounded to 2 decimals: pack_h (order to
# packed), dwell_h (packed to collected), transit_h (collected to delivered),
# total_h (order to delivered); then on_time_pct (1 decimal).
# Order by warehouse, period.
STAGE_SQL = """
-- TODO: your query here
"""

# BAND_SQL: one row per warehouse, period and packed_band: '00-16' when the
# parcel was packed before 16:00, '16-20' from 16:00 to before 20:00, '20-24'
# from 20:00. Columns: warehouse, period, packed_band, shipments, on_time_pct
# (1 decimal). Order by warehouse, period, packed_band.
BAND_SQL = """
-- TODO: your query here
"""


# ---- step 7 and 9: Python ------------------------------------------------

STAGES = ("pack", "dwell", "transit")


def stage_change(stage_rows):
    """For each warehouse that has both periods and each stage (pack, dwell,
    transit): dicts {warehouse, stage, before, after, change} where before and
    after are the average hours and change = after - before. Sorted by change,
    largest first; ties by warehouse then stage."""
    # TODO
    raise NotImplementedError


def _ts(text):
    return datetime.datetime.strptime(text, "%Y-%m-%d %H:%M")


def on_time_with_collection(shipments, warehouse, hour, first_week=7):
    """What-if: the after-period on-time rate (percent, all warehouses) if
    `warehouse` had a daily collection at `hour`:00 from `first_week` on.
    shipments: CSV rows (dicts of text). For each shipment of that warehouse
    ordered in week >= first_week, the new collection day is the packed day
    if packed before `hour`:00, else the next day. When that day is earlier
    than the actual collection day, move delivered_ts earlier by the same
    number of days. Only shipments ordered in week >= first_week count.
    None when there are none."""
    # TODO
    raise NotImplementedError


# ---- step 8: a chart you can paste into a message ------------------------

def text_chart(weekly, low=80.0, width=30):
    """One line per week: 'W01  94.3% ####'. The axis starts at `low`, not
    0, so the bar is (on_time_pct - low) / (100 - low) x width characters,
    rounded, and never below 0. Say so in the message: a cut axis exaggerates."""
    # TODO
    raise NotImplementedError
