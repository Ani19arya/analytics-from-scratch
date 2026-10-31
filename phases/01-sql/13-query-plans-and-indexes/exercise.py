"""Lesson 13: query plans and indexes. Your turn.

The dashboard's three tiles are in dashboard.py (do not edit it). Fill in
everything below, then run from this folder:
    python3 test_lesson.py

The goal: every tile gives the same answer as today, every tile reaches every
table with SEARCH (no SCAN line in its plan), the day and customer tiles do
at least 10 times less work than the dashboard did before the status index
existed, the month tile does less work than it did then, and you add at most
3 indexes (each one slows down every new order Tiffinbell writes).
"""


def plan(con, sql, params=()):
    """The detail lines of EXPLAIN QUERY PLAN for sql, in the order SQLite prints them."""
    # TODO
    raise NotImplementedError("plan")


def full_scans(con, sql, params=()):
    """Sorted, distinct names (as the plan prints them) on a line that starts with SCAN.
    Leave out the line SCAN CONSTANT ROW (a SELECT with no table)."""
    # TODO
    raise NotImplementedError("full_scans")


def count_steps(con, sql, params=()):
    """Run sql to the end and return how many times a progress handler set with
    con.set_progress_handler(callback, 1) was called. Remove the handler afterwards."""
    # TODO
    raise NotImplementedError("count_steps")


# TODO: names of existing indexes to drop (see dashboard.EXISTING_INDEXES).
DROP_INDEXES = []

# TODO: at most 3 CREATE INDEX statements.
CREATE_INDEXES = []

# TODO: one query per tile, same columns and same answers as dashboard.QUERIES,
# with the same named parameters.
FAST_QUERIES = {
    "customer_history": "",
    "day_summary": "",
    "city_month": "",
}
