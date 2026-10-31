"""Lesson 13: query plans and indexes. The worked answer.

Run the test against this file from the lesson folder:
    CHECK_SOLUTION=1 python3 test_lesson.py
"""


def plan(con, sql, params=()):
    """The detail lines of EXPLAIN QUERY PLAN for sql, in the order SQLite prints them."""
    # Each row is (id, parent, notused, detail); the detail is the readable part.
    return [row[3] for row in con.execute("EXPLAIN QUERY PLAN " + sql, params)]


def full_scans(con, sql, params=()):
    """Sorted, distinct names (as the plan prints them) that the plan reads from start to end."""
    names = set()
    for line in plan(con, sql, params):
        words = line.split()
        if len(words) >= 2 and words[0] == "SCAN" and line != "SCAN CONSTANT ROW":
            names.add(words[1])
    return sorted(names)


def count_steps(con, sql, params=()):
    """How many times SQLite calls a progress handler set to fire every 1 instruction while running sql."""
    calls = [0]

    def tick():
        calls[0] += 1
        return 0  # 0 means "carry on"; anything else would stop the query

    con.set_progress_handler(tick, 1)
    try:
        con.execute(sql, params).fetchall()
    finally:
        con.set_progress_handler(None, 1)
    return calls[0]


# The status index sends the month tile into a nested loop over customers, and
# steals the day tile from a better index. Drop it.
DROP_INDEXES = ["ix_orders_status"]

# Three indexes, one job each. The order of columns matters: an index on
# (customer_id, ordered_at) is sorted by customer first, then by time inside
# each customer, so "one customer, newest first" is a single short walk.
CREATE_INDEXES = [
    "CREATE INDEX ix_orders_customer_time ON orders (customer_id, ordered_at)",
    "CREATE INDEX ix_orders_time ON orders (ordered_at)",
    "CREATE UNIQUE INDEX ix_customers_id ON customers (customer_id)",
]

# The same answers as dashboard.QUERIES, written so an index on ordered_at can
# be used: the column stands alone on one side of each comparison.
FAST_QUERIES = {
    "customer_history": """
SELECT order_id, ordered_at, amount, status
FROM orders
WHERE customer_id = :customer_id
ORDER BY ordered_at DESC, order_id DESC
LIMIT 10""",
    "day_summary": """
SELECT COUNT(*) AS orders, SUM(amount) AS revenue
FROM orders
WHERE ordered_at >= :day
  AND ordered_at < date(:day, '+1 day')
  AND status = 'completed'""",
    "city_month": """
SELECT c.city, COUNT(*) AS orders, SUM(o.amount) AS revenue
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.ordered_at >= :month || '-01'
  AND o.ordered_at < date(:month || '-01', '+1 month')
  AND o.status = 'completed'
GROUP BY c.city
ORDER BY revenue DESC, c.city""",
}
