"""Case 03: marketing, is the campaign incremental? Worked answer.

Steps 7 to 9 of the case: one SQL query (SQLite) and the Python that turns it
into an answer. The campaign ran 1 to 28 September 2026 ('campaign' period);
4 to 31 August 2026 is the 'pre' period. In every segment a random 10% of
customers (grp 'holdout') got no campaign messages.
"""
import csv
import math
import os
import sqlite3

# ---- given: loading the CSVs into SQLite ---------------------------------


def load_db(folder):
    """Load audience.csv and daily.csv from `folder` into an in-memory SQLite database."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE audience (segment TEXT, grp TEXT, customers INTEGER)")
    con.execute("CREATE TABLE daily (date TEXT, segment TEXT, grp TEXT, orders INTEGER, code_orders INTEGER,"
                " revenue INTEGER, code_revenue INTEGER)")
    with open(os.path.join(folder, "audience.csv"), newline="") as f:
        con.executemany("INSERT INTO audience VALUES (?, ?, ?)",
                        [(r["segment"], r["grp"], int(r["customers"])) for r in csv.DictReader(f)])
    with open(os.path.join(folder, "daily.csv"), newline="") as f:
        con.executemany("INSERT INTO daily VALUES (?, ?, ?, ?, ?, ?, ?)",
                        [(r["date"], r["segment"], r["grp"], int(r["orders"]), int(r["code_orders"]),
                          int(r["revenue"]), int(r["code_revenue"])) for r in csv.DictReader(f)])
    return con


def query(con, sql):
    """Run sql and return a list of dicts, one per row."""
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


# ---- step 7: SQL ---------------------------------------------------------

# GROUP_SQL: one row per period, segment and grp in the audience. period is
# 'campaign' for dates from 2026-09-01 and 'pre' before that. Columns:
# period, segment, grp, customers (from audience), orders, code_orders,
# revenue, code_revenue (0, not NULL, for a group with no daily rows in a
# period). Every audience group appears in both periods.
# Order by period, segment, grp.
GROUP_SQL = """
WITH periods AS (SELECT 'campaign' AS period UNION ALL SELECT 'pre'),
d AS (
  SELECT CASE WHEN date >= '2026-09-01' THEN 'campaign' ELSE 'pre' END AS period,
         segment, grp, SUM(orders) AS orders, SUM(code_orders) AS code_orders,
         SUM(revenue) AS revenue, SUM(code_revenue) AS code_revenue
  FROM daily
  GROUP BY period, segment, grp
)
SELECT p.period, a.segment, a.grp, a.customers,
       COALESCE(d.orders, 0) AS orders, COALESCE(d.code_orders, 0) AS code_orders,
       COALESCE(d.revenue, 0) AS revenue, COALESCE(d.code_revenue, 0) AS code_revenue
FROM audience a
CROSS JOIN periods p
LEFT JOIN d ON d.period = p.period AND d.segment = a.segment AND d.grp = a.grp
ORDER BY p.period, a.segment, a.grp
"""


# ---- step 7 and 9: Python ------------------------------------------------

def lift(rows, segment, period="campaign", z=1.96):
    """The campaign's incremental orders in one segment, from rows of GROUP_SQL.
    rate = orders / customers for each grp. incremental = (rate campaign -
    rate holdout) x campaign customers. Treat each group's orders as Poisson,
    so se = campaign customers x sqrt(orders_c / n_c^2 + orders_h / n_h^2);
    low and high = incremental -+ z x se.
    incremental_revenue = (revenue per customer campaign - holdout) x campaign customers.
    attributed = the campaign group's code_orders.
    Return {"segment", "rate_campaign", "rate_holdout", "incremental", "se", "low",
    "high", "incremental_revenue", "attributed", "code_revenue"}.
    None if either group is missing or has 0 customers."""
    g = {r["grp"]: r for r in rows if r["segment"] == segment and r["period"] == period}
    c, h = g.get("campaign"), g.get("holdout")
    if not c or not h or not c["customers"] or not h["customers"]:
        return None
    nc, nh = c["customers"], h["customers"]
    inc = (c["orders"] / nc - h["orders"] / nh) * nc
    se = nc * math.sqrt(c["orders"] / nc ** 2 + h["orders"] / nh ** 2)
    return {"segment": segment, "rate_campaign": c["orders"] / nc, "rate_holdout": h["orders"] / nh,
            "incremental": inc, "se": se, "low": inc - z * se, "high": inc + z * se,
            "incremental_revenue": (c["revenue"] / nc - h["revenue"] / nh) * nc,
            "attributed": c["code_orders"], "code_revenue": c["code_revenue"]}


def total_lift(rows, period="campaign", z=1.96):
    """Add up lift() over every segment in rows (segments in alphabetical
    order; segments where lift is None are skipped). incremental,
    incremental_revenue, attributed and code_revenue are sums; se is the
    square root of the sum of squared se; low and high use the total se.
    Return the same keys as lift() except the rates, with segment 'all'."""
    out = {"segment": "all", "incremental": 0.0, "se": 0.0, "incremental_revenue": 0.0,
           "attributed": 0, "code_revenue": 0}
    var = 0.0
    for seg in sorted({r["segment"] for r in rows}):
        s = lift(rows, seg, period, z)
        if s is None:
            continue
        for k in ("incremental", "incremental_revenue", "attributed", "code_revenue"):
            out[k] += s[k]
        var += s["se"] ** 2
    out["se"] = math.sqrt(var)
    out["low"] = out["incremental"] - z * out["se"]
    out["high"] = out["incremental"] + z * out["se"]
    return out


def campaign_profit(rows, segment, margin, discount, period="campaign"):
    """Extra gross profit the campaign made in a segment, from rows of GROUP_SQL.
    Revenue is after discounts; the cost of the goods is (1 - margin) of the
    list price. A code order's list price is its revenue / (1 - discount), so
    a group's gross profit = margin x revenue - (1 - margin) x code_revenue x discount / (1 - discount).
    Return (profit per customer campaign - profit per customer holdout) x
    campaign customers. None when lift() would be None."""
    g = {r["grp"]: r for r in rows if r["segment"] == segment and r["period"] == period}
    c, h = g.get("campaign"), g.get("holdout")
    if not c or not h or not c["customers"] or not h["customers"]:
        return None

    def per_customer(r):
        given = r["code_revenue"] * discount / (1 - discount)
        return (margin * r["revenue"] - (1 - margin) * given) / r["customers"]

    return (per_customer(c) - per_customer(h)) * c["customers"]


# ---- step 8: a chart you can paste into a message ------------------------

def text_chart(lifts, width=30):
    """lifts: results of lift(). Two lines per segment:
    '<segment padded to 8> credited <attributed, 6 wide> <bar of #>' and
    '<8 spaces> real     <incremental rounded, 6 wide> <bar of #>'.
    The largest number across all lines gets `width` characters; a negative
    incremental gets no bar."""
    top = max([abs(s["attributed"]) for s in lifts] + [max(0, s["incremental"]) for s in lifts] + [0])
    lines = []
    for s in lifts:
        a = int(round(s["attributed"] / top * width)) if top else 0
        i = int(round(max(0, s["incremental"]) / top * width)) if top else 0
        lines.append("%-8s credited %6d %s" % (s["segment"], s["attributed"], "#" * a))
        lines.append("%-8s real     %6d %s" % ("", int(round(s["incremental"])), "#" * i))
    return lines


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    con = load_db(os.path.join(here, "..", "data"))
    rows = query(con, GROUP_SQL)
    lifts = [lift(rows, s) for s in ("loyal", "recent", "lapsed")]
    for s in lifts:
        print(s, campaign_profit(rows, s["segment"], 0.40, 0.15))
    print(total_lift(rows))
    print("\n".join(text_chart(lifts)))
