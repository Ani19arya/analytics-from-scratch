"""Case 08: banking, which segments are profitable? Worked answer.

Steps 7 to 9 of the case: two SQL queries (SQLite) and the Python that turns
them into an answer. One row per customer for October 2025 to September 2026;
the rates table is an example rate card (fictional).
"""
import csv
import os
import sqlite3

# ---- given: loading the CSVs into SQLite ---------------------------------

def load_db(customers_path, rates_path):
    """Load both CSVs into an in-memory SQLite database (tables customers and rates)."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE customers (customer_id TEXT, segment TEXT, deposit_balance REAL,"
                " loan_balance REAL, fee_income REAL, branch_visits INTEGER, calls INTEGER,"
                " digital_sessions INTEGER, charge_off REAL)")
    con.execute("CREATE TABLE rates (item TEXT, value REAL)")
    with open(customers_path, newline="") as f:
        con.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        [[r["customer_id"], r["segment"], float(r["deposit_balance"]), float(r["loan_balance"]),
                          float(r["fee_income"]), int(r["branch_visits"]), int(r["calls"]),
                          int(r["digital_sessions"]), float(r["charge_off"])] for r in csv.DictReader(f)])
    with open(rates_path, newline="") as f:
        con.executemany("INSERT INTO rates VALUES (?, ?)",
                        [[r["item"], float(r["value"])] for r in csv.DictReader(f)])
    return con


def query(con, sql):
    """Run sql and return a list of dicts, one per row."""
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


# ---- step 7: SQL ---------------------------------------------------------

# PROFIT_SQL: one row per customer. Columns: customer_id, segment,
# revenue = deposit_balance x deposit_margin + loan_balance x loan_margin + fee_income,
# cost_to_serve = branch_visits x branch_visit + calls x call
#                 + digital_sessions x digital_session + account_fixed,
# charge_off, profit = revenue - cost_to_serve - charge_off.
# The rates come from the rates table (one row per item), not typed in.
# Money columns rounded to 2 decimals. Order by customer_id.
PROFIT_SQL = """
WITH r AS (
  SELECT MAX(CASE WHEN item = 'deposit_margin' THEN value END) AS dep,
         MAX(CASE WHEN item = 'loan_margin' THEN value END) AS loan,
         MAX(CASE WHEN item = 'branch_visit' THEN value END) AS visit,
         MAX(CASE WHEN item = 'call' THEN value END) AS call,
         MAX(CASE WHEN item = 'digital_session' THEN value END) AS digital,
         MAX(CASE WHEN item = 'account_fixed' THEN value END) AS fixed
  FROM rates
),
p AS (
  SELECT c.customer_id, c.segment,
         c.deposit_balance * r.dep + c.loan_balance * r.loan + c.fee_income AS revenue,
         c.branch_visits * r.visit + c.calls * r.call + c.digital_sessions * r.digital + r.fixed AS cost_to_serve,
         c.charge_off
  FROM customers c CROSS JOIN r
)
SELECT customer_id, segment, ROUND(revenue, 2) AS revenue, ROUND(cost_to_serve, 2) AS cost_to_serve,
       ROUND(charge_off, 2) AS charge_off, ROUND(revenue - cost_to_serve - charge_off, 2) AS profit
FROM p
ORDER BY customer_id
"""

# SEGMENT_SQL: one row per segment. Columns: segment, customers, revenue,
# cost_to_serve, charge_offs, profit, profit_per_customer, unprofitable
# (customers with profit below 0). Money rounded to 2 decimals, computed from
# unrounded customer values. Order by profit, largest first.
SEGMENT_SQL = """
WITH r AS (
  SELECT MAX(CASE WHEN item = 'deposit_margin' THEN value END) AS dep,
         MAX(CASE WHEN item = 'loan_margin' THEN value END) AS loan,
         MAX(CASE WHEN item = 'branch_visit' THEN value END) AS visit,
         MAX(CASE WHEN item = 'call' THEN value END) AS call,
         MAX(CASE WHEN item = 'digital_session' THEN value END) AS digital,
         MAX(CASE WHEN item = 'account_fixed' THEN value END) AS fixed
  FROM rates
),
p AS (
  SELECT c.segment,
         c.deposit_balance * r.dep + c.loan_balance * r.loan + c.fee_income AS revenue,
         c.branch_visits * r.visit + c.calls * r.call + c.digital_sessions * r.digital + r.fixed AS cost_to_serve,
         c.charge_off
  FROM customers c CROSS JOIN r
)
SELECT segment,
       COUNT(*) AS customers,
       ROUND(SUM(revenue), 2) AS revenue,
       ROUND(SUM(cost_to_serve), 2) AS cost_to_serve,
       ROUND(SUM(charge_off), 2) AS charge_offs,
       ROUND(SUM(revenue - cost_to_serve - charge_off), 2) AS profit,
       ROUND(SUM(revenue - cost_to_serve - charge_off) / COUNT(*), 2) AS profit_per_customer,
       SUM(revenue - cost_to_serve - charge_off < 0) AS unprofitable
FROM p
GROUP BY segment
ORDER BY profit DESC
"""


# ---- step 7 and 9: Python ------------------------------------------------

def even_allocation(segment_rows):
    """The shortcut many banks start with: split the total cost_to_serve
    equally per customer. Return {segment: revenue - charge_offs - customers x
    (total cost_to_serve / total customers)}. Empty input: {}."""
    n = sum(s["customers"] for s in segment_rows)
    if n == 0:
        return {}
    per = sum(s["cost_to_serve"] for s in segment_rows) / n
    return {s["segment"]: s["revenue"] - s["charge_offs"] - s["customers"] * per for s in segment_rows}


def flips(segment_rows):
    """Segments where the two methods disagree on the sign: profitable
    (profit >= 0) under one and loss-making under the other. Sorted by name."""
    even = even_allocation(segment_rows)
    return sorted(s["segment"] for s in segment_rows if (s["profit"] < 0) != (even[s["segment"]] < 0))


def top_share(profits, fraction):
    """Share of total profit earned by the most profitable `fraction` of
    customers: sort descending, take the first int(len(profits) x fraction)
    customers, divide their profit by the total. None when there are no
    customers or the total profit is not positive."""
    total = sum(profits)
    if not profits or total <= 0:
        return None
    k = int(len(profits) * fraction)
    return sum(sorted(profits, reverse=True)[:k]) / total


def whale_curve(profits):
    """The whale curve: cumulative profit with customers sorted from most to
    least profitable. Return a dict: total, peak (the highest cumulative
    profit), peak_ratio (peak / total, None when total is not positive),
    unprofitable (customers with profit below 0)."""
    cum = peak = 0.0
    for p in sorted(profits, reverse=True):
        cum += p
        peak = max(peak, cum)
    total = sum(profits)
    return {"total": total, "peak": peak, "peak_ratio": peak / total if total > 0 else None,
            "unprofitable": sum(1 for p in profits if p < 0)}


# ---- step 8: a chart you can paste into a message ------------------------

def text_chart(items, width=20):
    """items: (label, value) pairs; values can be negative. One line per item:
    the label padded to the longest label, the value with no decimals, then a
    bar: '#' for a positive value, '-' for a negative one. The largest absolute
    value gets `width` characters; others are scaled and rounded."""
    if not items:
        return []
    pad = max(len(label) for label, _ in items)
    top = max(abs(v) for _, v in items)
    lines = []
    for label, v in items:
        n = int(round(abs(v) / top * width)) if top > 0 else 0
        lines.append("%s %9.0f %s" % (label.ljust(pad), v, ("#" if v >= 0 else "-") * n))
    return lines


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    con = load_db(os.path.join(here, "..", "data", "customers.csv"), os.path.join(here, "..", "data", "rates.csv"))
    seg = query(con, SEGMENT_SQL)
    for s in seg:
        print(s)
    print(even_allocation(seg))
    print(flips(seg))
    profits = [r["profit"] for r in query(con, PROFIT_SQL)]
    print(whale_curve(profits), top_share(profits, 0.2))
    print("\n".join(text_chart([(s["segment"], s["profit"]) for s in seg])))
