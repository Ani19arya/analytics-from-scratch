"""Case 01: e-commerce, why is revenue falling? Your turn.

Steps 7 to 9 of the case: two SQL queries (SQLite) and the Python that turns
them into an answer. Q2 is 1 April to 30 June 2026, Q3 is 1 July to
30 September 2026. Revenue = sessions x conversion rate x average order value.
"""
import csv
import math
import os
import sqlite3

# ---- given: loading the CSVs into SQLite ---------------------------------


def load_db(folder):
    """Load sessions.csv and orders.csv from `folder` into an in-memory SQLite database."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE sessions (date TEXT, channel TEXT, sessions INTEGER)")
    con.execute("CREATE TABLE orders (order_id TEXT, order_date TEXT, channel TEXT, items INTEGER, revenue INTEGER)")
    with open(os.path.join(folder, "sessions.csv"), newline="") as f:
        con.executemany("INSERT INTO sessions VALUES (?, ?, ?)",
                        [(r["date"], r["channel"], int(r["sessions"])) for r in csv.DictReader(f)])
    with open(os.path.join(folder, "orders.csv"), newline="") as f:
        con.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
                        [(r["order_id"], r["order_date"], r["channel"], int(r["items"]), int(r["revenue"]))
                         for r in csv.DictReader(f)])
    return con


def query(con, sql):
    """Run sql and return a list of dicts, one per row."""
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


# ---- step 7: SQL ---------------------------------------------------------

# QUARTER_SQL: one row per quarter that had sessions ('Q2' for dates before
# 2026-07-01, 'Q3' from then on). Columns: quarter, sessions, orders, revenue
# (orders and revenue 0, not NULL, when a quarter had no orders). Sessions and
# orders live in different tables at different grains: do not let a join
# multiply one by the other. Order by quarter.
QUARTER_SQL = """
-- TODO: your query here
"""

# CHANNEL_SQL: one row per quarter and channel that had sessions.
# Columns: quarter, channel, sessions, orders, revenue (orders and revenue are
# 0, not NULL, for a channel with sessions but no orders). Order by quarter, channel.
CHANNEL_SQL = """
-- TODO: your query here
"""


# ---- step 7 and 9: Python ------------------------------------------------

def log_mean(a, b):
    """The logarithmic mean of two positive numbers: (b - a) / (ln b - ln a), or a when a == b."""
    if a == b:
        return a
    return (b - a) / (math.log(b) - math.log(a))


def lmdi(before, after):
    """Split the revenue change between two rows of QUARTER_SQL into three
    effects that add up exactly to after revenue - before revenue:
    revenue = sessions x conversion (orders / sessions) x basket (revenue / orders).
    Each effect = log_mean(revenue before, revenue after) x ln(factor after / factor before).
    Return {"sessions", "conversion", "basket"}. None if any factor is 0 in either row."""
    # TODO
    raise NotImplementedError


def mix_and_rate(channel_rows, before="Q2", after="Q3"):
    """Split the change in revenue per session (RPS) into a mix effect (the
    channels' shares of sessions moved) and a rate effect (RPS within each
    channel moved), with the midpoint method so the two add up exactly:
      mix  = sum over channels of (share after - share before) x (rps before + rps after) / 2
      rate = sum over channels of (rps after - rps before) x (share before + share after) / 2
    A channel missing in one quarter has share 0 there and the other quarter's
    RPS, so its whole effect is mix.
    Return {"rps_before", "rps_after", "mix", "rate", "by_channel": {channel: {"mix", "rate"}}}.
    None if either quarter has no sessions."""
    # TODO
    raise NotImplementedError


# ---- step 8: a chart you can paste into a message ------------------------

def waterfall(steps, width=30):
    """steps: [(label, value), ...]. The first and last are totals, drawn with
    '#'; the ones between are changes, drawn with '+' when positive and '-'
    when negative. The largest absolute value gets `width` characters; the
    others are scaled and rounded. Each line: label padded to 12, the value
    with thousands commas (and a sign for changes) right-aligned in 10, the bar.
    Example: 'Q2 revenue    1,652,329 ####' and 'sessions       +127,005 +++'."""
    # TODO
    raise NotImplementedError

