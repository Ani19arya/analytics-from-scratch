"""Run one SQL query against a lesson's CSV files and print the result as a table.

Run it from inside a lesson folder, so that ./data/ holds the CSVs:

    python3 ../query.py "SELECT status, COUNT(*) AS orders FROM orders GROUP BY status"
    python3 ../query.py my_query.sql

Each CSV in data/ becomes a table with the same name (data/orders.csv is the
table orders). Empty cells become NULL, whole numbers become integers and
decimals become real numbers, exactly as the lesson tests load them.
NULL is printed as NULL, so you can tell a missing value from a zero.

Python 3.9+ standard library only. Nothing is written to disk.
"""
import csv
import os
import sqlite3
import sys


def cast(value):
    if value == "":
        return None
    for kind in (int, float):
        try:
            return kind(value)
        except ValueError:
            pass
    return value


def load_folder(data_dir):
    con = sqlite3.connect(":memory:")
    for name in sorted(os.listdir(data_dir)):
        if not name.endswith(".csv"):
            continue
        with open(os.path.join(data_dir, name), newline="") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            continue
        cols = list(rows[0].keys())
        con.execute("CREATE TABLE %s (%s)" % (name[:-4], ", ".join(cols)))
        con.executemany(
            "INSERT INTO %s VALUES (%s)" % (name[:-4], ", ".join("?" * len(cols))),
            [[cast(r[c]) for c in cols] for r in rows],
        )
    return con


def show(value):
    return "NULL" if value is None else str(value)


def print_table(headers, rows):
    cells = [headers] + [[show(v) for v in r] for r in rows]
    widths = [max(len(row[i]) for row in cells) for i in range(len(headers))]
    lines = ["  ".join(c.ljust(w) for c, w in zip(row, widths)).rstrip() for row in cells]
    lines.insert(1, "  ".join("-" * w for w in widths))
    print("\n".join(lines))


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    arg = argv[1]
    sql = open(arg).read() if arg.endswith(".sql") and os.path.isfile(arg) else arg
    data_dir = os.path.join(os.getcwd(), "data")
    if not os.path.isdir(data_dir):
        print("No data/ folder here. Run this from a lesson folder, for example phases/01-sql/01-group-by-from-raw-rows.")
        return 2
    con = load_folder(data_dir)
    try:
        cur = con.execute(sql)
    except sqlite3.Error as e:
        print("SQLite error: %s" % e)
        return 1
    if cur.description is None:
        print("(the statement ran and returned no table)")
        return 0
    print_table([d[0] for d in cur.description], cur.fetchall())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
