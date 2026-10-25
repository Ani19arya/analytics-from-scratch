"""Solution: check SQL that an LLM wrote against a trusted answer."""
import csv
import os
import sqlite3

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def load_db(data_dir=DATA):
    """Load the CSVs into an in-memory sqlite database with typed columns."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, country TEXT)")
    conn.execute("CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER, order_date TEXT, status TEXT, amount REAL)")
    with open(os.path.join(data_dir, "customers.csv"), newline="") as f:
        conn.executemany("INSERT INTO customers VALUES (?, ?)",
                         [(int(r["customer_id"]), r["country"]) for r in csv.DictReader(f)])
    with open(os.path.join(data_dir, "orders.csv"), newline="") as f:
        conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
                         [(int(r["order_id"]), int(r["customer_id"]), r["order_date"], r["status"], float(r["amount"]))
                          for r in csv.DictReader(f)])
    return conn


def load_queries(data_dir=DATA):
    with open(os.path.join(data_dir, "llm_queries.csv"), newline="") as f:
        return list(csv.DictReader(f))


def run_query(conn, sql):
    """Return (rows, None) on success or (None, error_message) on failure."""
    try:
        return conn.execute(sql).fetchall(), None
    except sqlite3.Error as e:
        return None, str(e)


def normalize(rows):
    """Make results comparable: round floats to 2 places, ignore row order and column names."""
    out = []
    for row in rows:
        out.append(tuple(round(v, 2) if isinstance(v, float) else v for v in row))
    return sorted(out, key=repr)


def classify(conn, llm_sql, trusted_sql):
    """Return 'correct', 'wrong rows' or 'error'."""
    llm_rows, err = run_query(conn, llm_sql)
    if err is not None:
        return "error"
    trusted_rows, terr = run_query(conn, trusted_sql)
    if terr is not None:
        raise ValueError("trusted query failed: " + terr)
    return "correct" if normalize(llm_rows) == normalize(trusted_rows) else "wrong rows"


def main():
    conn = load_db()
    for q in load_queries():
        print(q["query_id"], classify(conn, q["llm_sql"], q["trusted_sql"]).ljust(11), q["question"])


if __name__ == "__main__":
    main()
