"""Lesson 10: from standard library to pandas. Your turn.

Write the six functions below, each with the same rules as its pandas call (defaults included),
with None playing the part of NaN. Then fill in PANDAS_EQUIVALENT: for each function, the pandas
call with the arguments that make it behave the same.
Run from this folder: python3 test_lesson.py   (works without pandas; with pandas it also
compares your answers with pandas' own)
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
TYPES = {"qty": int, "amount": float}

PANDAS_EQUIVALENT = {
    "read_typed": "TODO",
    "filter_rows": "TODO",
    "group_agg": "TODO",
    "sort_rows": "TODO",
    "drop_duplicates": "TODO",
    "value_counts": "TODO",
}


def read_typed(path, types=TYPES, na_values=("",)):
    """Rows as dicts. A cell whose text is in na_values becomes None; other cells in a
    column listed in types are converted with that type; the rest stay text."""
    # TODO
    raise NotImplementedError


def filter_rows(rows, column, op, value):
    """Rows where `row[column] op value` holds, for op in ==, !=, >, >=, <, <= (anything else is
    a ValueError). Compare the way pandas does: what does NaN != "EU" give?"""
    # TODO
    raise NotImplementedError


def group_agg(rows, by, column, how, dropna=True):
    """{group value: result}, groups sorted, a None group last. how is "sum", "mean", "count" or
    "size" (anything else is a ValueError). Match pandas for a group whose values are all None,
    and for rows whose group value is None when dropna is True or False."""
    # TODO
    raise NotImplementedError


def sort_rows(rows, column, ascending=True):
    """A stable sort on one column, None last whichever way you sort."""
    # TODO
    raise NotImplementedError


def drop_duplicates(rows, subset=None, keep="first"):
    """Rows whose values in subset (every column when None) were not seen before.
    keep is "first", "last" or False (drop every copy). None equals None here."""
    # TODO
    raise NotImplementedError


def value_counts(rows, column, dropna=True):
    """{value: number of rows}, most common first, ties in order of first appearance.
    dropna=True leaves out None."""
    # TODO
    raise NotImplementedError


def main():
    rows = drop_duplicates(read_typed(os.path.join(DATA, "orders.csv")))
    by_region = group_agg(rows, "region", "amount", "sum", dropna=False)
    total = sum(r["amount"] for r in rows if r["amount"] is not None)
    for region, amount in by_region.items():
        print("%-8s %12.2f" % ("(blank)" if region is None else region, amount))
    print("%-8s %12.2f" % ("total", sum(by_region.values())))
    print("check: total of every amount %.2f" % total)


if __name__ == "__main__":
    main()
