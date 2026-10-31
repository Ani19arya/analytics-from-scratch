"""Solution: a gateway that runs model-written SQL so it can read only what it is allowed to read."""
import csv
import os
import pathlib
import sqlite3
import time

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
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


# ---------- the gateway ----------

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
    count = 0
    has_code = False
    i, n = 0, len(sql)
    while i < n:
        j = _skip(sql, i)
        if j != i:
            i = j
            continue
        ch = sql[i]
        if ch in "'\"`[":
            close = "]" if ch == "[" else ch
            j = i + 1
            while True:
                j = sql.find(close, j)
                if j == -1 or close == "]" or not sql.startswith(close * 2, j):
                    break
                j += 2  # a doubled quote is an escaped quote, still inside
            has_code = True
            i = n if j == -1 else j + 1
            continue
        if ch == ";":
            if has_code:
                count += 1
            has_code = False
        else:
            has_code = True
        i += 1
    if has_code:
        count += 1
    return count


def first_keyword(sql):
    """The first word of sql in upper case, skipping whitespace and comments. '' if there is none."""
    i = _skip(sql, 0)
    j = i
    while j < len(sql) and (sql[j].isalpha() or sql[j] == "_"):
        j += 1
    return sql[i:j].upper()


def make_authorizer(reasons, allowed_tables=ALLOWED_TABLES, blocked_columns=BLOCKED_COLUMNS):
    """Return a callback for conn.set_authorizer. It allows only reads of allowed tables and
    columns, and appends a reason to the list `reasons` every time it refuses something.

    SQLite calls it as authorize(action, arg1, arg2, db_name, trigger) while it prepares a
    statement. For SQLITE_READ, arg1 is the table and arg2 the column ('' for COUNT(*)).
    db_name is None when arg1 is a WITH (CTE) name rather than a stored table.
    Return sqlite3.SQLITE_OK to allow and sqlite3.SQLITE_DENY to refuse.
    """
    def authorize(action, arg1, arg2, db_name, trigger):
        if action not in READ_ACTIONS:
            reasons.append("%s is not allowed" % ACTION_NAMES.get(action, "action %d" % action))
            return sqlite3.SQLITE_DENY
        # db_name is None when the "table" is a WITH (CTE) name, not a stored table
        if action == sqlite3.SQLITE_READ and db_name is not None:
            if arg1 not in allowed_tables:
                reasons.append("table %s is not allowed" % arg1)
                return sqlite3.SQLITE_DENY
            if (arg1, arg2) in blocked_columns:
                reasons.append("column %s.%s is not allowed" % (arg1, arg2))
                return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    return authorize


def open_readonly(path):
    """Open the database file so that no statement on this connection can change it."""
    conn = sqlite3.connect(pathlib.Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON")
    return conn


def run_question(path, sql, max_rows=MAX_ROWS, max_seconds=MAX_SECONDS):
    """Run one model-written query through every wall. Return {"status", "reason", "rows"}.

    status is ok, truncated (more than max_rows rows: the first max_rows are returned),
    blocked (refused before or while preparing; reason says why), timeout, or error.
    rows is None unless status is ok or truncated.
    """
    statements = count_statements(sql)
    if statements != 1:
        return {"status": "blocked", "reason": "empty query" if statements == 0 else "more than one statement", "rows": None}
    keyword = first_keyword(sql)
    if keyword not in ("SELECT", "WITH"):
        return {"status": "blocked", "reason": "starts with %s, only SELECT or WITH is allowed" % keyword, "rows": None}
    conn = open_readonly(path)
    reasons = []
    conn.set_authorizer(make_authorizer(reasons))
    deadline = time.monotonic() + max_seconds
    conn.set_progress_handler(lambda: time.monotonic() > deadline, 1000)
    try:
        rows = conn.execute(sql).fetchmany(max_rows + 1)
    except sqlite3.Error as e:
        if reasons:
            return {"status": "blocked", "reason": "; ".join(sorted(set(reasons))), "rows": None}
        if "interrupted" in str(e):
            return {"status": "timeout", "reason": "took longer than %.1f seconds" % max_seconds, "rows": None}
        return {"status": "error", "reason": str(e), "rows": None}
    finally:
        conn.close()
    if len(rows) > max_rows:
        return {"status": "truncated", "reason": "more than %d rows" % max_rows, "rows": rows[:max_rows]}
    return {"status": "ok", "reason": "", "rows": rows}


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
