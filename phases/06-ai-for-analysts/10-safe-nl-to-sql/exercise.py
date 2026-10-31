"""Exercise: a gateway that runs model-written SQL so it can read only what it is allowed to read.

Fill in the five functions marked TODO. Then run: python3 test_lesson.py
"""
import csv
import os
import pathlib
import sqlite3
import time

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
ALLOWED_TABLES = {"customers", "orders"}
BLOCKED_COLUMNS = {("customers", "email")}
MAX_ROWS = 500
MAX_SECONDS = 0.5
SCHEMA = {
    "customers": "CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, name TEXT, email TEXT, country TEXT, signup_date TEXT)",
    "orders": "CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER, order_date TEXT, status TEXT, amount REAL)",
    "staff_pay": "CREATE TABLE staff_pay (staff_id INTEGER PRIMARY KEY, name TEXT, annual_salary INTEGER)",
}
# Authorizer action codes that are reads. Everything else is refused.
READ_ACTIONS = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}
ACTION_NAMES = {sqlite3.SQLITE_INSERT: "INSERT", sqlite3.SQLITE_UPDATE: "UPDATE", sqlite3.SQLITE_DELETE: "DELETE",
                sqlite3.SQLITE_PRAGMA: "PRAGMA", sqlite3.SQLITE_ATTACH: "ATTACH", sqlite3.SQLITE_DETACH: "DETACH",
                sqlite3.SQLITE_CREATE_TABLE: "CREATE TABLE", sqlite3.SQLITE_DROP_TABLE: "DROP TABLE",
                sqlite3.SQLITE_TRANSACTION: "TRANSACTION"}


# ---------- given: build the database file from the CSVs ----------


def load_tables(data_dir=DATA):
    tables = {}
    for name in SCHEMA:
        with open(os.path.join(data_dir, name + ".csv"), newline="") as f:
            tables[name] = list(csv.DictReader(f))
    return tables


def load_questions(data_dir=DATA):
    with open(os.path.join(data_dir, "nl_questions.csv"), newline="") as f:
        return list(csv.DictReader(f))


def build_db(path, tables):
    """Write the three tables to a new SQLite file at path (replacing any old one)."""
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    for name, ddl in SCHEMA.items():
        conn.execute(ddl)
        rows = tables[name]
        if rows:
            cols = list(rows[0].keys())
            conn.executemany("INSERT INTO %s (%s) VALUES (%s)" % (name, ", ".join(cols), ", ".join("?" * len(cols))),
                             [[r[c] for c in cols] for r in rows])
    conn.commit()
    conn.close()


# ---------- the gateway: _skip is given, the rest is yours ----------


def _skip(sql, i):
    """Index of the next character at or after i that is not whitespace or inside a comment."""
    n = len(sql)
    while i < n:
        if sql[i].isspace():
            i += 1
        elif sql.startswith("--", i):
            j = sql.find("\n", i)
            i = n if j == -1 else j + 1
        elif sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            i = n if j == -1 else j + 2
        else:
            return i
    return n


def count_statements(sql):
    """How many statements sql holds. A ; inside quotes or a comment does not count,
    and an empty piece between two ; is not a statement."""
    # TODO
    raise NotImplementedError


def first_keyword(sql):
    """The first word of sql in upper case, skipping whitespace and comments. '' if there is none."""
    # TODO
    raise NotImplementedError


def make_authorizer(reasons, allowed_tables=ALLOWED_TABLES, blocked_columns=BLOCKED_COLUMNS):
    """Return a callback for conn.set_authorizer. It allows only reads of allowed tables and
    columns, and appends a reason to the list `reasons` every time it refuses something.

    SQLite calls it as authorize(action, arg1, arg2, db_name, trigger) while it prepares a
    statement. For SQLITE_READ, arg1 is the table and arg2 the column ('' for COUNT(*)).
    db_name is None when arg1 is a WITH (CTE) name rather than a stored table.
    Return sqlite3.SQLITE_OK to allow and sqlite3.SQLITE_DENY to refuse.
    """
    # TODO
    raise NotImplementedError


def open_readonly(path):
    """Open the database file so that no statement on this connection can change it."""
    # TODO: two locks, see the README: open with a "file:...?mode=ro" URI, then PRAGMA query_only
    raise NotImplementedError


def run_question(path, sql, max_rows=MAX_ROWS, max_seconds=MAX_SECONDS):
    """Run one model-written query through every wall. Return {"status", "reason", "rows"}.

    status is ok, truncated (more than max_rows rows: the first max_rows are returned),
    blocked (refused before or while preparing; reason says why), timeout, or error.
    rows is None unless status is ok or truncated.
    """
    # TODO
    raise NotImplementedError


def main():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "shop.db")
        build_db(path, load_tables())
        for q in load_questions():
            result = run_question(path, q["llm_sql"])
            shown = "%d rows" % len(result["rows"]) if result["rows"] is not None else result["reason"]
            print("%s %-9s %s" % (q["question_id"], result["status"], shown))


if __name__ == "__main__":
    main()
