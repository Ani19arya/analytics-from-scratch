"""Solution: check SQL that an LLM wrote against a trusted answer, safely, on two databases."""
import csv
import itertools
import os
import re
import sqlite3
import time

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
MAX_ROWS = 10000
MAX_SECONDS = 2.0
TOLERANCE = 0.005
WRITE_WORDS = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|ATTACH|DETACH|PRAGMA|VACUUM|REINDEX|REPLACE\s+INTO)\b", re.I)


def make_db(tables):
    """Load {"customers": [...], "orders": [...]} into an in-memory database, then make it read-only."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, country TEXT)")
    conn.execute("CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER, order_date TEXT, status TEXT, amount REAL)")
    conn.executemany("INSERT INTO customers VALUES (?, ?)", tables["customers"])
    conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", tables["orders"])
    conn.commit()
    # From here on this connection refuses every write, whatever SQL it is given.
    conn.execute("PRAGMA query_only = ON")
    return conn


def read_tables(data_dir):
    with open(os.path.join(data_dir, "customers.csv"), newline="") as f:
        customers = [(int(r["customer_id"]), r["country"]) for r in csv.DictReader(f)]
    with open(os.path.join(data_dir, "orders.csv"), newline="") as f:
        orders = [(int(r["order_id"]), int(r["customer_id"]) if r["customer_id"] else None,
                   r["order_date"], r["status"], float(r["amount"])) for r in csv.DictReader(f)]
    return {"customers": customers, "orders": orders}


def load_db(data_dir=DATA):
    """Database 1 from data/, or any folder holding customers.csv and orders.csv."""
    return make_db(read_tables(data_dir))


def load_dbs(data_dir=DATA):
    """The two databases every query is checked on."""
    return [load_db(data_dir), load_db(os.path.join(data_dir, "db2"))]


def load_queries(data_dir=DATA):
    with open(os.path.join(data_dir, "llm_queries.csv"), newline="") as f:
        return list(csv.DictReader(f))


def strip_strings_and_comments(sql):
    """Blank out 'text', "names" and comments so their contents cannot fool the checks."""
    sql = re.sub(r"'(?:[^']|'')*'", "''", sql)
    sql = re.sub(r'"(?:[^"]|"")*"', '""', sql)
    sql = re.sub(r"--[^\n]*", " ", sql)
    return re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)


def is_ranked(trusted_sql):
    """Order is part of the answer when the trusted query sorts."""
    return re.search(r"\bORDER\s+BY\b", strip_strings_and_comments(trusted_sql), re.I) is not None


def guard(sql):
    """Return None if sql is one read-only SELECT or WITH statement, else the reason it is refused."""
    code = strip_strings_and_comments(sql).strip()
    if code.endswith(";"):
        code = code[:-1].rstrip()
    if not code:
        return "empty query"
    if ";" in code:
        return "more than one statement"
    first = code.split(None, 1)[0].upper()
    if first not in ("SELECT", "WITH"):
        return "starts with %s, only SELECT or WITH is allowed" % first
    found = WRITE_WORDS.search(code)
    if found:
        return "contains %s" % found.group(1).upper()
    return None


def run_query(conn, sql, max_rows=MAX_ROWS, max_seconds=MAX_SECONDS):
    """Return (rows, None) on success or (None, error_message) on failure, with a row cap and a time limit."""
    deadline = time.monotonic() + max_seconds
    conn.set_progress_handler(lambda: time.monotonic() > deadline, 10000)
    try:
        rows = conn.execute(sql).fetchmany(max_rows + 1)
    except (sqlite3.Error, sqlite3.Warning) as e:
        return None, str(e)
    finally:
        conn.set_progress_handler(None, 0)
    if len(rows) > max_rows:
        return None, "more than %d rows" % max_rows
    return rows, None


def same_value(a, b, tol=TOLERANCE):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol
    return a == b


def same_row(a, b):
    return len(a) == len(b) and all(same_value(x, y) for x, y in zip(a, b))


def same_rows(got, want, ordered):
    """Row by row in order, or as a multiset: each wanted row must use up one matching row."""
    if len(got) != len(want):
        return False
    if ordered:
        return all(same_row(g, w) for g, w in zip(got, want))
    left = list(got)
    for w in want:
        for i, g in enumerate(left):
            if same_row(g, w):
                del left[i]
                break
        else:
            return False
    return True


def same_result(got, want, ordered=False):
    """True if some order of got's columns makes it equal to want. Column names are never compared."""
    if not got or not want:
        return not got and not want
    width = len(want[0])
    if len(got[0]) != width:
        return False
    for perm in itertools.permutations(range(width)):
        moved = [tuple(row[i] for i in perm) for row in got]
        if same_rows(moved, want, ordered):
            return True
    return False


def classify_on(conn, llm_sql, trusted_sql):
    """'correct', 'wrong rows' or 'error' on one database."""
    llm_rows, err = run_query(conn, llm_sql)
    if err is not None:
        return "error"
    trusted_rows, terr = run_query(conn, trusted_sql)
    if terr is not None:
        raise ValueError("trusted query failed: " + terr)
    return "correct" if same_result(llm_rows, trusted_rows, is_ranked(trusted_sql)) else "wrong rows"


def classify(dbs, llm_sql, trusted_sql):
    """Return 'blocked', 'error', 'wrong rows' or 'correct'. dbs is one connection or a list of them."""
    if isinstance(dbs, sqlite3.Connection):
        dbs = [dbs]
    if guard(llm_sql) is not None:
        return "blocked"
    for conn in dbs:
        label = classify_on(conn, llm_sql, trusted_sql)
        if label != "correct":
            return label
    return "correct"


def main():
    dbs = load_dbs()
    print("query  db1         db2         label")
    for q in load_queries():
        reason = guard(q["llm_sql"])
        if reason:
            print(q["query_id"].ljust(6), "blocked: " + reason)
            continue
        per_db = [classify_on(conn, q["llm_sql"], q["trusted_sql"]) for conn in dbs]
        label = classify(dbs, q["llm_sql"], q["trusted_sql"])
        print(q["query_id"].ljust(6), per_db[0].ljust(11), per_db[1].ljust(11), label)


if __name__ == "__main__":
    main()
