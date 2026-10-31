"""Case 02: SaaS, reduce subscription churn. Worked answer.

Steps 7 to 9 of the case: two SQL queries (SQLite) and the Python that turns
them into an answer. The data is observed at the end of October 2026
(AS_OF). A customer's tenure is counted in whole months from the signup
month: to the churn month if they left, to AS_OF if they are still active.
"""
import csv
import os
import sqlite3

AS_OF = "2026-10"

# ---- given: loading the CSV into SQLite ----------------------------------


def load_db(path):
    """Load customers.csv into an in-memory SQLite table called customers.
    A blank churn_month (still active) becomes NULL."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE customers (customer_id TEXT, signup_month TEXT, plan TEXT, seats INTEGER,"
                " mrr INTEGER, onboarded TEXT, churn_month TEXT)")
    with open(path, newline="") as f:
        rows = [(r["customer_id"], r["signup_month"], r["plan"], int(r["seats"]), int(r["mrr"]),
                 r["onboarded"], r["churn_month"] or None) for r in csv.DictReader(f)]
    con.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    return con


def query(con, sql):
    """Run sql and return a list of dicts, one per row."""
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


# ---- step 7: SQL ---------------------------------------------------------

# LIFE_SQL: a life table per plan. One row per plan and tenure month n, from 1
# to the longest tenure in the data. Columns: plan, tenure_month,
# at_risk (customers whose tenure is n or more: still subscribed at the start
# of month n), churned (customers who left with tenure exactly n),
# hazard_pct = 100 x churned / at_risk rounded to 2 decimals (NULL when
# at_risk is 0). Tenure = months from signup_month to churn_month, or to
# '2026-10' for active customers. Order by plan, tenure_month.
LIFE_SQL = """
WITH RECURSIVE c AS (
  SELECT plan,
         (CAST(substr(COALESCE(churn_month, '2026-10'), 1, 4) AS INTEGER) * 12
          + CAST(substr(COALESCE(churn_month, '2026-10'), 6, 2) AS INTEGER))
       - (CAST(substr(signup_month, 1, 4) AS INTEGER) * 12
          + CAST(substr(signup_month, 6, 2) AS INTEGER)) AS tenure,
         churn_month IS NOT NULL AS left_flag
  FROM customers
),
months(n) AS (
  SELECT 1
  UNION ALL
  SELECT n + 1 FROM months WHERE n < (SELECT MAX(tenure) FROM c)
)
SELECT c.plan, months.n AS tenure_month,
       SUM(c.tenure >= months.n) AS at_risk,
       SUM(c.left_flag AND c.tenure = months.n) AS churned,
       ROUND(100.0 * SUM(c.left_flag AND c.tenure = months.n) / NULLIF(SUM(c.tenure >= months.n), 0), 2) AS hazard_pct
FROM c CROSS JOIN months
GROUP BY c.plan, months.n
ORDER BY c.plan, months.n
"""

# SEGMENT_SQL: one row per plan, onboarded and size. size is '1-2' for 1 or
# 2 seats, '3+' otherwise. Columns: plan, onboarded, size, customers,
# churned, customer_months (the sum of every customer's tenure, as above),
# active_customers, active_mrr (MRR of customers still active),
# churned_mrr (MRR of customers who left). Order by plan, onboarded, size.
SEGMENT_SQL = """
WITH c AS (
  SELECT plan, onboarded, CASE WHEN seats <= 2 THEN '1-2' ELSE '3+' END AS size, mrr,
         churn_month IS NOT NULL AS left_flag,
         (CAST(substr(COALESCE(churn_month, '2026-10'), 1, 4) AS INTEGER) * 12
          + CAST(substr(COALESCE(churn_month, '2026-10'), 6, 2) AS INTEGER))
       - (CAST(substr(signup_month, 1, 4) AS INTEGER) * 12
          + CAST(substr(signup_month, 6, 2) AS INTEGER)) AS tenure
  FROM customers
)
SELECT plan, onboarded, size,
       COUNT(*) AS customers,
       SUM(left_flag) AS churned,
       SUM(tenure) AS customer_months,
       SUM(1 - left_flag) AS active_customers,
       SUM(CASE WHEN left_flag THEN 0 ELSE mrr END) AS active_mrr,
       SUM(CASE WHEN left_flag THEN mrr ELSE 0 END) AS churned_mrr
FROM c
GROUP BY plan, onboarded, size
ORDER BY plan, onboarded, size
"""


# ---- step 7 and 9: Python ------------------------------------------------

def survival(life_rows, plan):
    """The share of a plan's customers still subscribed after each tenure month:
    S(n) = product over months 1..n of (1 - churned / at_risk).
    Return [(tenure_month, survival), ...] in order, stopping before the first
    month with nobody at risk. [] when the plan has no rows."""
    out = []
    s = 1.0
    for r in sorted((r for r in life_rows if r["plan"] == plan), key=lambda r: r["tenure_month"]):
        if not r["at_risk"]:
            break
        s *= 1 - r["churned"] / r["at_risk"]
        out.append((r["tenure_month"], s))
    return out


def monthly_hazard(segment):
    """Churned / customer_months: the chance a customer leaves in any one
    month they are subscribed. None when customer_months is 0."""
    if not segment["customer_months"]:
        return None
    return segment["churned"] / segment["customer_months"]


def lever(segments, field, from_value, to_value):
    """What changing customers from `from_value` to `to_value` on `field`
    (for example onboarded 'no' to 'yes') would keep, per month, if their
    monthly hazard fell to that of the matching segment (same values on the
    other two of plan, onboarded, size) with `to_value`.
    For each matched pair: kept = active x max(0, hazard from - hazard to),
    for MRR (active_mrr) and for customers (active_customers).
    Pairs where either hazard is None, or with no match, are skipped.
    Return {"mrr_kept": ..., "customers_kept": ...}."""
    keys = ("plan", "onboarded", "size")
    index = {tuple(s[k] for k in keys): s for s in segments}
    out = {"mrr_kept": 0.0, "customers_kept": 0.0}
    for s in segments:
        if s[field] != from_value:
            continue
        ref_key = tuple(to_value if k == field else s[k] for k in keys)
        ref = index.get(ref_key)
        if ref is None:
            continue
        h_from, h_to = monthly_hazard(s), monthly_hazard(ref)
        if h_from is None or h_to is None:
            continue
        gap = max(0.0, h_from - h_to)
        out["mrr_kept"] += s["active_mrr"] * gap
        out["customers_kept"] += s["active_customers"] * gap
    return out


def churn_shares(segments, field):
    """For each value of `field`, its share of all churned customers and of
    all churned MRR, as fractions: {value: {"customers": ..., "mrr": ...}}.
    A share is None when nobody churned at all."""
    tc = sum(s["churned"] for s in segments)
    tm = sum(s["churned_mrr"] for s in segments)
    out = {}
    for s in segments:
        e = out.setdefault(s[field], [0, 0])
        e[0] += s["churned"]
        e[1] += s["churned_mrr"]
    return {v: {"customers": c / tc if tc else None, "mrr": m / tm if tm else None} for v, (c, m) in out.items()}


# ---- step 8: a chart you can paste into a message ------------------------

def text_chart(points, width=30):
    """points: [(label, fraction between 0 and 1), ...]. One line per point:
    the label padded to 10, the percent with 1 decimal in 6 characters, then a
    bar of round(fraction x width) '#' characters (the scale is fixed: 100%
    is `width`, so curves on different charts compare)."""
    return ["%-10s %5.1f%% %s" % (label, 100 * v, "#" * int(round(v * width))) for label, v in points]


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    con = load_db(os.path.join(here, "..", "data", "customers.csv"))
    life = query(con, LIFE_SQL)
    for plan in ("monthly", "annual"):
        curve = dict(survival(life, plan))
        print(plan)
        print("\n".join(text_chart([("month %d" % t, curve[t]) for t in (1, 3, 6, 12, 18) if t in curve])))
    seg = query(con, SEGMENT_SQL)
    for s in seg:
        print(s, monthly_hazard(s))
    print("onboarding", lever(seg, "onboarded", "no", "yes"))
    print("size", lever(seg, "size", "1-2", "3+"))
    print(churn_shares(seg, "size"))
