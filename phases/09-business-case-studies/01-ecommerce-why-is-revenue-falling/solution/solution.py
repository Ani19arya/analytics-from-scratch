"""Case 01: e-commerce, why is revenue falling? Worked answer.

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
WITH s AS (
  SELECT CASE WHEN date < '2026-07-01' THEN 'Q2' ELSE 'Q3' END AS quarter, SUM(sessions) AS sessions
  FROM sessions GROUP BY quarter
),
o AS (
  SELECT CASE WHEN order_date < '2026-07-01' THEN 'Q2' ELSE 'Q3' END AS quarter,
         COUNT(*) AS orders, SUM(revenue) AS revenue
  FROM orders GROUP BY quarter
)
SELECT s.quarter, s.sessions, COALESCE(o.orders, 0) AS orders, COALESCE(o.revenue, 0) AS revenue
FROM s LEFT JOIN o ON o.quarter = s.quarter
ORDER BY s.quarter
"""

# CHANNEL_SQL: one row per quarter and channel that had sessions.
# Columns: quarter, channel, sessions, orders, revenue (orders and revenue are
# 0, not NULL, for a channel with sessions but no orders). Order by quarter, channel.
CHANNEL_SQL = """
WITH s AS (
  SELECT CASE WHEN date < '2026-07-01' THEN 'Q2' ELSE 'Q3' END AS quarter, channel,
         SUM(sessions) AS sessions
  FROM sessions GROUP BY quarter, channel
),
o AS (
  SELECT CASE WHEN order_date < '2026-07-01' THEN 'Q2' ELSE 'Q3' END AS quarter, channel,
         COUNT(*) AS orders, SUM(revenue) AS revenue
  FROM orders GROUP BY quarter, channel
)
SELECT s.quarter, s.channel, s.sessions,
       COALESCE(o.orders, 0) AS orders, COALESCE(o.revenue, 0) AS revenue
FROM s LEFT JOIN o ON o.quarter = s.quarter AND o.channel = s.channel
ORDER BY s.quarter, s.channel
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
    if 0 in (before["sessions"], before["orders"], before["revenue"],
             after["sessions"], after["orders"], after["revenue"]):
        return None
    w = log_mean(before["revenue"], after["revenue"])
    out = {}
    for name, f in (("sessions", lambda r: r["sessions"]),
                    ("conversion", lambda r: r["orders"] / r["sessions"]),
                    ("basket", lambda r: r["revenue"] / r["orders"])):
        out[name] = w * math.log(f(after) / f(before))
    return out


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
    rows = {(r["quarter"], r["channel"]): r for r in channel_rows}
    tot = {q: sum(r["sessions"] for (qq, _), r in rows.items() if qq == q) for q in (before, after)}
    if not tot[before] or not tot[after]:
        return None
    out = {"rps_before": 0.0, "rps_after": 0.0, "mix": 0.0, "rate": 0.0, "by_channel": {}}
    for ch in sorted({c for _, c in rows}):
        b, a = rows.get((before, ch)), rows.get((after, ch))
        sb = b["sessions"] / tot[before] if b else 0.0
        sa = a["sessions"] / tot[after] if a else 0.0
        rb = b["revenue"] / b["sessions"] if b and b["sessions"] else None
        ra = a["revenue"] / a["sessions"] if a and a["sessions"] else None
        if rb is None:
            rb = ra if ra is not None else 0.0
        if ra is None:
            ra = rb
        mix = (sa - sb) * (rb + ra) / 2
        rate = (ra - rb) * (sb + sa) / 2
        out["by_channel"][ch] = {"mix": mix, "rate": rate}
        out["mix"] += mix
        out["rate"] += rate
        out["rps_before"] += sb * rb
        out["rps_after"] += sa * ra
    return out


# ---- step 8: a chart you can paste into a message ------------------------

def waterfall(steps, width=30):
    """steps: [(label, value), ...]. The first and last are totals, drawn with
    '#'; the ones between are changes, drawn with '+' when positive and '-'
    when negative. The largest absolute value gets `width` characters; the
    others are scaled and rounded. Each line: label padded to 12, the value
    with thousands commas (and a sign for changes) right-aligned in 10, the bar.
    Example: 'Q2 revenue    1,652,329 ####' and 'sessions       +127,005 +++'."""
    if not steps:
        return []
    top = max(abs(v) for _, v in steps)
    lines = []
    for i, (label, value) in enumerate(steps):
        n = int(round(abs(value) / top * width)) if top else 0
        if i in (0, len(steps) - 1):
            lines.append("%-12s %10s %s" % (label, "{:,.0f}".format(value), "#" * n))
        else:
            lines.append("%-12s %10s %s" % (label, "{:+,.0f}".format(value), ("+" if value > 0 else "-") * n))
    return lines


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    con = load_db(os.path.join(here, "..", "data"))
    q = query(con, QUARTER_SQL)
    print(q)
    eff = lmdi(q[0], q[1])
    print(eff)
    ch = query(con, CHANNEL_SQL)
    print(mix_and_rate(ch))
    print("\n".join(waterfall([("Q2 revenue", q[0]["revenue"])] + list(eff.items()) + [("Q3 revenue", q[1]["revenue"])])))
