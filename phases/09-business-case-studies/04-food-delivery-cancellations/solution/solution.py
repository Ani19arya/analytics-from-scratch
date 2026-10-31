"""Case 04: food delivery, why are cancellations rising? Worked answer.

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
SELECT CAST((julianday(order_date) - julianday('2026-08-03')) / 7 AS INTEGER) + 1 AS week,
       COUNT(*) AS orders,
       SUM(status = 'cancelled') AS cancelled,
       ROUND(100.0 * SUM(status = 'cancelled') / COUNT(*), 1) AS cancel_rate_pct
FROM orders
GROUP BY week
ORDER BY week
"""

# REASON_SQL: cancellations by period and cancel_reason. period is 'before'
# (weeks 1 to 6) or 'after' (weeks 7 to 12). Columns: period, cancel_reason,
# cancelled, per_100_orders = 100 x cancelled / ALL orders in that period,
# rounded to 2 decimals. Only reasons that occur; order by period, cancel_reason.
REASON_SQL = """
WITH tagged AS (
  SELECT CASE WHEN julianday(order_date) - julianday('2026-08-03') < 42
              THEN 'before' ELSE 'after' END AS period,
         cancel_reason
  FROM orders
),
totals AS (SELECT period, COUNT(*) AS orders FROM tagged GROUP BY period)
SELECT t.period, t.cancel_reason, COUNT(*) AS cancelled,
       ROUND(100.0 * COUNT(*) / o.orders, 2) AS per_100_orders
FROM tagged t
JOIN totals o ON o.period = t.period
WHERE t.cancel_reason IS NOT NULL
GROUP BY t.period, t.cancel_reason, o.orders
ORDER BY t.period, t.cancel_reason
"""

# SEGMENT_SQL: columns city, app_version, period, orders, cancelled.
# Order by city, app_version, period.
SEGMENT_SQL = """
SELECT city, app_version,
       CASE WHEN julianday(order_date) - julianday('2026-08-03') < 42
            THEN 'before' ELSE 'after' END AS period,
       COUNT(*) AS orders,
       SUM(status = 'cancelled') AS cancelled
FROM orders
GROUP BY city, app_version, period
ORDER BY city, app_version, period
"""


# ---- step 7 and 9: Python ------------------------------------------------

def excess_by_segment(segments):
    """segments: rows of SEGMENT_SQL. For each (city, app_version) in the after
    period, expected = after orders x the city's before cancel rate (all versions
    together). A city with no before orders uses the overall before rate.
    Return dicts {city, app_version, orders, cancelled, expected, excess},
    sorted by excess, largest first; ties by city then app_version."""
    city_before = {}
    all_before = [0, 0]
    for s in segments:
        if s["period"] == "before":
            c = city_before.setdefault(s["city"], [0, 0])
            c[0] += s["orders"]
            c[1] += s["cancelled"]
            all_before[0] += s["orders"]
            all_before[1] += s["cancelled"]
    overall = all_before[1] / all_before[0] if all_before[0] else 0.0
    out = []
    for s in segments:
        if s["period"] != "after":
            continue
        o, c = city_before.get(s["city"], (0, 0))
        rate = c / o if o else overall
        expected = s["orders"] * rate
        out.append({"city": s["city"], "app_version": s["app_version"], "orders": s["orders"],
                    "cancelled": s["cancelled"], "expected": expected,
                    "excess": s["cancelled"] - expected})
    out.sort(key=lambda r: (-r["excess"], r["city"], r["app_version"]))
    return out


def top_segment_share(excess_rows):
    """The first row's excess divided by the total excess of all rows.
    It can be above 1 when other segments got better. None when there are
    no rows or the total excess is not positive."""
    total = sum(r["excess"] for r in excess_rows)
    if not excess_rows or total <= 0:
        return None
    return excess_rows[0]["excess"] / total


def rate_without(segments, city, app_version):
    """The after-period cancel rate in percent with one (city, app_version)
    segment taken out: what the business would look like without it.
    None when no after orders are left."""
    orders = cancelled = 0
    for s in segments:
        if s["period"] == "after" and (s["city"], s["app_version"]) != (city, app_version):
            orders += s["orders"]
            cancelled += s["cancelled"]
    return 100.0 * cancelled / orders if orders else None


# ---- step 8: a chart you can paste into a message ------------------------

def text_chart(weekly, width=30):
    """One line per week: 'W01   4.7% ####'. The longest bar (the highest
    rate) has `width` characters; the others are scaled and rounded."""
    if not weekly:
        return []
    top = max(w["cancel_rate_pct"] for w in weekly)
    lines = []
    for w in weekly:
        bar = int(round(w["cancel_rate_pct"] / top * width)) if top > 0 else 0
        lines.append("W%02d %5.1f%% %s" % (w["week"], w["cancel_rate_pct"], "#" * bar))
    return lines


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    con = load_db(os.path.join(here, "..", "data", "orders.csv"))
    print("\n".join(text_chart(query(con, WEEKLY_SQL))))
    for r in query(con, REASON_SQL):
        print(r)
    ex = excess_by_segment(query(con, SEGMENT_SQL))
    for r in ex:
        print("%-7s %-6s orders %4d cancelled %3d expected %5.1f excess %5.1f" % (
            r["city"], r["app_version"], r["orders"], r["cancelled"], r["expected"], r["excess"]))
    print("top segment share of excess: %.3f" % top_segment_share(ex))
    top = ex[0]
    print("after-period rate without %s %s: %.2f%%" % (
        top["city"], top["app_version"], rate_without(query(con, SEGMENT_SQL), top["city"], top["app_version"])))
