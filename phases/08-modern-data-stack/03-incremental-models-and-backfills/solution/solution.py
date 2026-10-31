"""Lesson 08-03 solution: an incremental daily revenue model, its lookback, and backfills."""
import csv
import datetime
import os
import sqlite3

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
COLUMNS = ["load_date", "order_id", "order_date", "status", "amount"]


# Given helpers.

def read_raw(data_dir=DATA):
    with open(os.path.join(data_dir, "raw_orders.csv"), newline="") as f:
        return list(csv.DictReader(f))


def load_raw(con, rows=None):
    """Create raw_orders and insert the rows exactly as they landed."""
    rows = read_raw() if rows is None else rows
    con.execute("DROP TABLE IF EXISTS raw_orders")
    con.execute("CREATE TABLE raw_orders (load_date TEXT, order_id INTEGER, order_date TEXT, status TEXT, amount TEXT)")
    con.executemany("INSERT INTO raw_orders VALUES (?, ?, ?, ?, ?)", [[r[c] for c in COLUMNS] for r in rows])
    return con


def shift(day, days):
    """shift('2026-10-01', -3) == '2026-09-28'."""
    return (datetime.date.fromisoformat(day) + datetime.timedelta(days=days)).isoformat()


def table_rows(con):
    """{order_date: (orders, delivered_orders, revenue)} from daily_revenue, or {} when it does not exist."""
    if not con.execute("SELECT 1 FROM sqlite_master WHERE name = 'daily_revenue'").fetchone():
        return {}
    return {r[0]: (r[1], r[2], r[3]) for r in
            con.execute("SELECT order_date, orders, delivered_orders, revenue FROM daily_revenue")}


# The model.

CREATE = """CREATE TABLE IF NOT EXISTS daily_revenue (
  order_date TEXT PRIMARY KEY, orders INTEGER, delivered_orders INTEGER, revenue REAL)"""

DAYS_SQL = """
WITH visible AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY load_date DESC) AS rn
  FROM raw_orders
  WHERE load_date <= :as_of
)
SELECT order_date,
       COUNT(*) AS orders,
       SUM(status = 'delivered') AS delivered_orders,
       ROUND(COALESCE(SUM(CASE WHEN status = 'delivered' THEN CAST(amount AS REAL) END), 0), 2) AS revenue
FROM visible
WHERE rn = 1 AND order_date BETWEEN :lo AND :hi
GROUP BY order_date
"""


def build_days(con, lo, hi, as_of):
    """Rewrite daily_revenue for every order_date from lo to hi (both included),
    from the raw rows that had landed by as_of. Returns how many day rows were written."""
    con.execute(CREATE)
    con.execute("DELETE FROM daily_revenue WHERE order_date BETWEEN ? AND ?", (lo, hi))
    cur = con.execute("INSERT INTO daily_revenue " + DAYS_SQL, {"lo": lo, "hi": hi, "as_of": as_of})
    return cur.rowcount


def full_rebuild(con, as_of):
    """Drop daily_revenue and build every day from scratch, as the data stood on as_of."""
    con.execute("DROP TABLE IF EXISTS daily_revenue")
    return build_days(con, "0000-01-01", "9999-12-31", as_of)


def incremental_run(con, run_date, lookback_days):
    """The nightly run on run_date: rewrite the window run_date - lookback_days .. run_date."""
    return build_days(con, shift(run_date, -lookback_days), run_date, run_date)


def backfill(con, start, end, as_of):
    """Rewrite the days start .. end with everything that had landed by as_of."""
    return build_days(con, start, end, as_of)


def required_lookback(con):
    """The longest delay, in days, between an order_date and a load_date in raw_orders (0 when empty)."""
    row = con.execute("SELECT MAX(julianday(load_date) - julianday(order_date)) FROM raw_orders").fetchone()
    return int(row[0]) if row[0] is not None else 0


def stale_days(con_a, con_b):
    """Sorted order_dates where daily_revenue differs between two databases
    (a day missing from one of them counts as different)."""
    a, b = table_rows(con_a), table_rows(con_b)
    return sorted(d for d in set(a) | set(b) if a.get(d) != b.get(d))


if __name__ == "__main__":
    full = load_raw(sqlite3.connect(":memory:"))
    full_rebuild(full, "2026-10-31")
    for lookback in (3, required_lookback(full)):
        inc = load_raw(sqlite3.connect(":memory:"))
        full_rebuild(inc, "2026-09-01")
        day = "2026-09-02"
        while day <= "2026-10-31":
            incremental_run(inc, day, lookback)
            day = shift(day, 1)
        print("lookback", lookback, "stale days:", stale_days(inc, full))
