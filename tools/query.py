#!/usr/bin/env python3
"""Run any SQL against a lesson's CSV files.

Usage (from the repo root):

    python3 tools/query.py <lesson-folder> "<SQL>"
    python3 tools/query.py <lesson-folder>            # list the tables and columns

Example:

    python3 tools/query.py phases/00-start-here/04-your-first-sql-query "SELECT * FROM orders LIMIT 5"

What it does:
1. Loads every data/*.csv in the lesson folder into an in-memory SQLite table
   named after the file (data/orders.csv becomes the table orders).
2. Stores each value as a whole number, a decimal number or text, whichever fits.
   An empty CSV cell becomes NULL.
3. Runs your SQL and prints the result as an aligned table, then the row count.

Nothing is written to disk. The CSV files are never changed.
Python 3.9 or later, standard library only.
"""
import csv
import os
import sqlite3
import sys


def cast(text):
    """Turn one CSV cell into None, an int, a float or the original text."""
    if text == "":
        return None
    for kind in (int, float):
        try:
            return kind(text)
        except ValueError:
            pass
    return text


def load(folder):
    data = os.path.join(folder, "data")
    if not os.path.isdir(data):
        sys.exit("No data/ folder in %s. Pass a lesson folder, for example "
                 "phases/00-start-here/04-your-first-sql-query" % folder)
    con = sqlite3.connect(":memory:")
    tables = {}
    for name in sorted(os.listdir(data)):
        if not name.endswith(".csv"):
            continue
        table = name[:-4]
        with open(os.path.join(data, name), newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = [[cast(v) for v in row] for row in reader]
        cols = ", ".join('"%s"' % c for c in header)
        con.execute('CREATE TABLE "%s" (%s)' % (table, cols))
        con.executemany('INSERT INTO "%s" VALUES (%s)' % (table, ", ".join("?" * len(header))), rows)
        tables[table] = (header, len(rows))
    if not tables:
        sys.exit("No CSV files in %s" % data)
    return con, tables


def show(value):
    if value is None:
        return "NULL"
    return str(value)


def print_table(header, rows):
    cells = [[show(v) for v in row] for row in rows]
    widths = [len(h) for h in header]
    for row in cells:
        for i, c in enumerate(row):
            widths[i] = max(widths[i], len(c))
    numeric = [all(isinstance(r[i], (int, float)) or r[i] is None for r in rows) and rows != [] for i in range(len(header))]

    def line(values):
        out = []
        for i, v in enumerate(values):
            out.append(v.rjust(widths[i]) if numeric[i] else v.ljust(widths[i]))
        return " | ".join(out).rstrip()

    print(line(header))
    print("-+-".join("-" * w for w in widths))
    for row in cells:
        print(line(row))
    print("(%d row%s)" % (len(rows), "" if len(rows) == 1 else "s"))


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0 if len(argv) >= 2 else 1
    con, tables = load(argv[1])
    if len(argv) < 3:
        for table, (header, n) in tables.items():
            print("%s (%d rows): %s" % (table, n, ", ".join(header)))
        return 0
    sql = argv[2]
    try:
        cur = con.execute(sql)
    except sqlite3.Error as err:
        print("SQL error: %s" % err)
        print("Tables you can use: %s" % ", ".join(tables))
        return 1
    if cur.description is None:
        print("(no result)")
        return 0
    header = [d[0] for d in cur.description]
    print_table(header, cur.fetchall())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
