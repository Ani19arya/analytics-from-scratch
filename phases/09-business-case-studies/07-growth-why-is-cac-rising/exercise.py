"""Case 07: growth, why is acquisition cost rising? Your turn.

Steps 7 to 9 of the case: three SQL queries (SQLite) and the Python that turns
them into an answer. Weeks run Monday to Sunday from 5 January 2026: weeks 1 to
13 are Q1, 14 to 26 are Q2 and 27 to 39 are Q3.
"""
import csv
import os
import sqlite3

PAID = ("search", "social", "video")

# ---- given: loading the CSVs into SQLite ---------------------------------

def load_db(spend_path, acq_path):
    """Load both CSVs into an in-memory SQLite database (tables spend and acquisitions)."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE spend (week_start TEXT, channel TEXT, spend REAL)")
    con.execute("CREATE TABLE acquisitions (week_start TEXT, channel TEXT, platform TEXT,"
                " signups INTEGER, subscribers INTEGER)")
    with open(spend_path, newline="") as f:
        con.executemany("INSERT INTO spend VALUES (?, ?, ?)",
                        [[r["week_start"], r["channel"], float(r["spend"])] for r in csv.DictReader(f)])
    with open(acq_path, newline="") as f:
        con.executemany("INSERT INTO acquisitions VALUES (?, ?, ?, ?, ?)",
                        [[r["week_start"], r["channel"], r["platform"], int(r["signups"]), int(r["subscribers"])]
                         for r in csv.DictReader(f)])
    return con


def query(con, sql):
    """Run sql and return a list of dicts, one per row."""
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


# ---- step 7: SQL ---------------------------------------------------------

# QUARTER_SQL: one row per quarter ('Q1', 'Q2', 'Q3') and channel that appears
# in acquisitions. Columns: quarter, channel, spend (total, rounded to 2
# decimals; 0 for organic and unattributed), signups, subscribers.
# Order by quarter, channel. Careful: spend has one row per week and channel,
# acquisitions one per week, channel and platform.
QUARTER_SQL = """
-- TODO: your query here
"""

# PLATFORM_SQL: one row per quarter and platform. Columns: quarter, platform,
# subscribers (all channels), unattributed (subscribers whose channel is
# 'unattributed'). Order by quarter, platform.
PLATFORM_SQL = """
-- TODO: your query here
"""

# WEEKLY_SQL: one row per week (1 to 39). Columns: week, paid_spend,
# paid_subscribers (search, social and video), reported_cac (paid_spend /
# paid_subscribers, rounded to 2 decimals, NULL when there are none),
# ios_unattributed_pct (100 x unattributed iOS subscribers / all iOS
# subscribers, rounded to 1 decimal). Order by week.
WEEKLY_SQL = """
-- TODO: your query here
"""


# ---- step 7 and 9: Python ------------------------------------------------

def reported_cac(quarter_rows, quarter):
    """The CAC the dashboard shows: total paid spend / subscribers attributed
    to paid channels (search, social, video) in that quarter. None when there
    are no such subscribers."""
    # TODO
    raise NotImplementedError


def channel_cac(quarter_rows):
    """{(quarter, channel): spend / subscribers} for paid channels only.
    The value is None when the channel has no subscribers that quarter."""
    # TODO
    raise NotImplementedError


def excess_unattributed(platform_rows, base="Q1", target="Q3"):
    """{platform: excess} for each platform in the target quarter, where
    excess = unattributed in target - target subscribers x the platform's
    unattributed share in the base quarter. A platform with no base
    subscribers has a base share of 0. Excess can be negative."""
    # TODO
    raise NotImplementedError


def decompose(quarter_rows, platform_rows, base="Q1", target="Q3"):
    """Split the reported CAC change into a tracking part and a real part.
    Returns a dict with:
      cac_base, cac_target (reported CAC in each quarter),
      cac_corrected (target paid spend / (target paid subscribers + the sum
        of the positive excess unattributed across platforms)),
      change_pct (100 x (cac_target / cac_base - 1)),
      tracking_pts (100 x (cac_target - cac_corrected) / cac_base),
      real_pts (100 x (cac_corrected - cac_base) / cac_base).
    tracking_pts + real_pts equals change_pct."""
    # TODO
    raise NotImplementedError


def marginal_cac(spend_a, subs_a, spend_b, subs_b):
    """Cost of each extra subscriber between two periods:
    (spend_b - spend_a) / (subs_b - subs_a). None when subscribers did not
    grow (subs_b <= subs_a)."""
    # TODO
    raise NotImplementedError


def trial_to_paid(quarter_rows):
    """{quarter: subscribers / signups} over all channels. None for a quarter
    with no signups. This is the pricing check: a price rise shows up here."""
    # TODO
    raise NotImplementedError


# ---- step 8: a chart you can paste into a message ------------------------

def text_chart(items, width=30):
    """items: (label, value) pairs with value >= 0 (None counts as 0). One
    line per item: the label padded to the longest label, the value with one
    decimal, then a bar of '#'. The largest value gets `width` characters;
    others are scaled and rounded. All values 0: no bars."""
    # TODO
    raise NotImplementedError
