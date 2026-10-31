"""A tiny warehouse in SQLite: load the raw layer, then build every model from it.

You do not need to change this file. It is the "platform" your SQL runs on.

- load_raw(con, tables=None) creates raw_orders and raw_customers and fills them
  from data/*.csv (or from the dicts make_data.build(seed) returns).
- read_models(path) reads a .sql file split by "-- model: <name>" lines into an
  ordered list of (name, select_sql).
- build(con, models) drops and recreates one table per model, in file order,
  as CREATE TABLE <name> AS <select>. It refuses to write to a raw_ table and
  refuses anything that is not a SELECT (or WITH ... SELECT), so a model can only
  read the layers below it.
- rebuild(models, tables=None) does both on a fresh in-memory database. Because
  every model is built from raw, the same raw data always gives the same tables.
- fingerprint(con, table) is a short hash of a table's sorted rows, to compare
  two builds or to prove raw was not touched.

Python 3.9+ standard library only.
"""
import csv
import hashlib
import os
import re
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
RAW = {
    "raw_orders": [("load_id", "INTEGER"), ("order_id", "INTEGER"), ("customer_id", "INTEGER"),
                   ("ordered_at", "TEXT"), ("status", "TEXT"), ("amount", "TEXT"), ("discount", "TEXT")],
    "raw_customers": [("load_id", "INTEGER"), ("customer_id", "INTEGER"), ("city", "TEXT"),
                      ("signup_date", "TEXT")],
}


def read_csv_tables(data_dir=DATA):
    tables = {}
    for name in RAW:
        with open(os.path.join(data_dir, name + ".csv"), newline="") as f:
            tables[name] = list(csv.DictReader(f))
    return tables


def load_raw(con, tables=None):
    """Create the raw tables and insert the rows exactly as they arrived."""
    if tables is None:
        tables = read_csv_tables()
    for name, cols in RAW.items():
        con.execute("DROP TABLE IF EXISTS %s" % name)
        con.execute("CREATE TABLE %s (%s)" % (name, ", ".join("%s %s" % c for c in cols)))
        con.executemany("INSERT INTO %s VALUES (%s)" % (name, ", ".join("?" * len(cols))),
                        [[r[c] for c, _ in cols] for r in tables.get(name, [])])
    return con


def read_models(path):
    """[(name, sql), ...] in file order. Comment lines are dropped; empty models are kept as ''."""
    models, name, buf = [], None, []
    with open(path) as f:
        for line in f:
            m = re.match(r"\s*--\s*model:\s*(\w+)", line)
            if m:
                if name:
                    models.append((name, "".join(buf).strip()))
                name, buf = m.group(1), []
            elif name is not None and not line.strip().startswith("--"):
                buf.append(line)
    if name:
        models.append((name, "".join(buf).strip()))
    return models


def build(con, models):
    """Build each model as a table, in order. Raises ValueError for a model that is empty or not a SELECT."""
    for name, sql in models:
        if name.startswith("raw_"):
            raise ValueError("model %s would overwrite the raw layer, which is never edited" % name)
        body = sql.strip().rstrip(";")
        if not re.match(r"(?is)^\s*(select|with)\b", body):
            raise ValueError("model %s must be a single SELECT (or WITH ... SELECT); it is: %r" % (name, body[:60]))
        con.execute("DROP TABLE IF EXISTS %s" % name)
        con.execute("CREATE TABLE %s AS %s" % (name, body))
    return con


def rebuild(models, tables=None):
    """A fresh in-memory warehouse: load raw, build every model. Returns the connection."""
    con = sqlite3.connect(":memory:")
    load_raw(con, tables)
    return build(con, models)


def rows(con, table, order_by=None):
    sql = "SELECT * FROM %s" % table
    if order_by:
        sql += " ORDER BY " + order_by
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def fingerprint(con, table):
    """First 12 hex digits of a hash of the table's rows, sorted. Same rows, same fingerprint."""
    data = sorted(repr(tuple(r)) for r in con.execute("SELECT * FROM %s" % table))
    return hashlib.sha256("\n".join(data).encode()).hexdigest()[:12]
