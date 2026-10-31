"""Exercise: pivot a long table to wide and back with csv and dict only.

load_csv, write_csv and main are done for you. Fill in the functions marked TODO.
Then run: python3 test_lesson.py
"""
import csv
import os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def load_csv(name, data_dir=DATA):
    with open(os.path.join(data_dir, name), newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)


def pivot_wider(rows, index, columns, values, duplicates="error"):
    """Long to wide. Returns (header, wide_rows).

    One output row per distinct value of `index`, one column per distinct value of
    `columns`, both in order of first appearance. A missing pair becomes "".
    Two input rows for the same pair raise ValueError (duplicates="error"), or are
    added up as integers (duplicates="sum"), which is what a spreadsheet pivot table
    does by default. Never overwrite one with the other.
    """
    # TODO: collect row keys and column keys in first-appearance order, store each
    # cell in a dict keyed by (row key, column key), deal with a repeated pair as
    # `duplicates` says (any other value of duplicates is a ValueError too), then
    # build one dict per row key with "" for missing cells. Keep cells as strings.
    raise NotImplementedError


def pivot_longer(wide_rows, id_col, var_name, value_name):
    """Wide to long. Every non-id column becomes a row; empty cells are skipped."""
    # TODO: skip only "", so a real "0" stays.
    raise NotImplementedError


def same_rows(a, b):
    """True when a and b hold the same rows, in any order. Repeated rows must repeat equally often."""
    # TODO: turn each row dict into a sorted tuple of its items, then compare sorted lists.
    raise NotImplementedError


def total_by(long_rows, key, value):
    """Sum `value` for each distinct `key`. One loop, whatever the key is."""
    # TODO
    raise NotImplementedError


def main():
    long_rows = load_csv("sales_long.csv")
    header, wide = pivot_wider(long_rows, "region", "month", "revenue")
    print(",".join(header))
    for r in wide:
        print(",".join(str(r[h]) for h in header))
    back = pivot_longer(wide, "region", "month", "revenue")
    print("long rows in:", len(long_rows), " long rows back:", len(back),
          " same rows:", same_rows(back, long_rows), " same order:", back == long_rows)
    print("total by month:", total_by(long_rows, "month", "revenue"))


if __name__ == "__main__":
    main()
