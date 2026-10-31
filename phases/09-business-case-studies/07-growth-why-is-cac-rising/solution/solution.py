"""Case 07: growth, why is acquisition cost rising? Worked answer.

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
WITH a AS (
  SELECT 'Q' || ((CAST((julianday(week_start) - julianday('2026-01-05')) / 7 AS INTEGER)) / 13 + 1) AS quarter,
         channel, SUM(signups) AS signups, SUM(subscribers) AS subscribers
  FROM acquisitions
  GROUP BY quarter, channel
),
s AS (
  SELECT 'Q' || ((CAST((julianday(week_start) - julianday('2026-01-05')) / 7 AS INTEGER)) / 13 + 1) AS quarter,
         channel, SUM(spend) AS spend
  FROM spend
  GROUP BY quarter, channel
)
SELECT a.quarter, a.channel, ROUND(COALESCE(s.spend, 0), 2) AS spend, a.signups, a.subscribers
FROM a
LEFT JOIN s ON s.quarter = a.quarter AND s.channel = a.channel
ORDER BY a.quarter, a.channel
"""

# PLATFORM_SQL: one row per quarter and platform. Columns: quarter, platform,
# subscribers (all channels), unattributed (subscribers whose channel is
# 'unattributed'). Order by quarter, platform.
PLATFORM_SQL = """
SELECT 'Q' || ((CAST((julianday(week_start) - julianday('2026-01-05')) / 7 AS INTEGER)) / 13 + 1) AS quarter,
       platform,
       SUM(subscribers) AS subscribers,
       SUM(CASE WHEN channel = 'unattributed' THEN subscribers ELSE 0 END) AS unattributed
FROM acquisitions
GROUP BY quarter, platform
ORDER BY quarter, platform
"""

# WEEKLY_SQL: one row per week (1 to 39). Columns: week, paid_spend,
# paid_subscribers (search, social and video), reported_cac (paid_spend /
# paid_subscribers, rounded to 2 decimals, NULL when there are none),
# ios_unattributed_pct (100 x unattributed iOS subscribers / all iOS
# subscribers, rounded to 1 decimal). Order by week.
WEEKLY_SQL = """
WITH a AS (
  SELECT week_start,
         SUM(CASE WHEN channel IN ('search', 'social', 'video') THEN subscribers ELSE 0 END) AS paid_subscribers,
         SUM(CASE WHEN platform = 'ios' AND channel = 'unattributed' THEN subscribers ELSE 0 END) AS ios_unattr,
         SUM(CASE WHEN platform = 'ios' THEN subscribers ELSE 0 END) AS ios_subs
  FROM acquisitions GROUP BY week_start
),
s AS (SELECT week_start, SUM(spend) AS paid_spend FROM spend GROUP BY week_start)
SELECT CAST((julianday(a.week_start) - julianday('2026-01-05')) / 7 AS INTEGER) + 1 AS week,
       ROUND(COALESCE(s.paid_spend, 0), 2) AS paid_spend,
       a.paid_subscribers,
       ROUND(s.paid_spend / NULLIF(a.paid_subscribers, 0), 2) AS reported_cac,
       ROUND(100.0 * a.ios_unattr / NULLIF(a.ios_subs, 0), 1) AS ios_unattributed_pct
FROM a LEFT JOIN s ON s.week_start = a.week_start
ORDER BY week
"""


# ---- step 7 and 9: Python ------------------------------------------------

def reported_cac(quarter_rows, quarter):
    """The CAC the dashboard shows: total paid spend / subscribers attributed
    to paid channels (search, social, video) in that quarter. None when there
    are no such subscribers."""
    spend = sum(r["spend"] for r in quarter_rows if r["quarter"] == quarter and r["channel"] in PAID)
    subs = sum(r["subscribers"] for r in quarter_rows if r["quarter"] == quarter and r["channel"] in PAID)
    return spend / subs if subs else None


def channel_cac(quarter_rows):
    """{(quarter, channel): spend / subscribers} for paid channels only.
    The value is None when the channel has no subscribers that quarter."""
    out = {}
    for r in quarter_rows:
        if r["channel"] in PAID:
            out[(r["quarter"], r["channel"])] = r["spend"] / r["subscribers"] if r["subscribers"] else None
    return out


def excess_unattributed(platform_rows, base="Q1", target="Q3"):
    """{platform: excess} for each platform in the target quarter, where
    excess = unattributed in target - target subscribers x the platform's
    unattributed share in the base quarter. A platform with no base
    subscribers has a base share of 0. Excess can be negative."""
    base_share = {}
    for r in platform_rows:
        if r["quarter"] == base:
            base_share[r["platform"]] = r["unattributed"] / r["subscribers"] if r["subscribers"] else 0.0
    out = {}
    for r in platform_rows:
        if r["quarter"] == target:
            out[r["platform"]] = r["unattributed"] - r["subscribers"] * base_share.get(r["platform"], 0.0)
    return out


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
    c0 = reported_cac(quarter_rows, base)
    c1 = reported_cac(quarter_rows, target)
    spend = sum(r["spend"] for r in quarter_rows if r["quarter"] == target and r["channel"] in PAID)
    subs = sum(r["subscribers"] for r in quarter_rows if r["quarter"] == target and r["channel"] in PAID)
    extra = sum(max(0.0, v) for v in excess_unattributed(platform_rows, base, target).values())
    corrected = spend / (subs + extra)
    return {"cac_base": c0, "cac_target": c1, "cac_corrected": corrected,
            "change_pct": 100.0 * (c1 / c0 - 1),
            "tracking_pts": 100.0 * (c1 - corrected) / c0,
            "real_pts": 100.0 * (corrected - c0) / c0}


def marginal_cac(spend_a, subs_a, spend_b, subs_b):
    """Cost of each extra subscriber between two periods:
    (spend_b - spend_a) / (subs_b - subs_a). None when subscribers did not
    grow (subs_b <= subs_a)."""
    if subs_b <= subs_a:
        return None
    return (spend_b - spend_a) / (subs_b - subs_a)


def trial_to_paid(quarter_rows):
    """{quarter: subscribers / signups} over all channels. None for a quarter
    with no signups. This is the pricing check: a price rise shows up here."""
    agg = {}
    for r in quarter_rows:
        a = agg.setdefault(r["quarter"], [0, 0])
        a[0] += r["subscribers"]
        a[1] += r["signups"]
    return {q: (s / n if n else None) for q, (s, n) in agg.items()}


# ---- step 8: a chart you can paste into a message ------------------------

def text_chart(items, width=30):
    """items: (label, value) pairs with value >= 0 (None counts as 0). One
    line per item: the label padded to the longest label, the value with one
    decimal, then a bar of '#'. The largest value gets `width` characters;
    others are scaled and rounded. All values 0: no bars."""
    if not items:
        return []
    vals = [(label, v or 0.0) for label, v in items]
    pad = max(len(label) for label, _ in vals)
    top = max(v for _, v in vals)
    lines = []
    for label, v in vals:
        bar = int(round(v / top * width)) if top > 0 else 0
        lines.append("%s %6.1f %s" % (label.ljust(pad), v, "#" * bar))
    return lines


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    con = load_db(os.path.join(here, "..", "data", "spend.csv"), os.path.join(here, "..", "data", "acquisitions.csv"))
    q = query(con, QUARTER_SQL)
    p = query(con, PLATFORM_SQL)
    for r in q:
        print(r)
    print(channel_cac(q))
    print(excess_unattributed(p))
    print(decompose(q, p))
    print(trial_to_paid(q))
