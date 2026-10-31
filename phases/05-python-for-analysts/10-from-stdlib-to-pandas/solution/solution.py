"""Lesson 10 solution: six table operations in the standard library, each with pandas' rules.

Run: python3 solution/solution.py   (revenue by region, the careful way)
Each function behaves like the pandas call in PANDAS_EQUIVALENT, defaults included, so the
test can compare the two when pandas is installed. None plays the part of NaN.
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
TYPES = {"qty": int, "amount": float}

PANDAS_EQUIVALENT = {
    "read_typed": 'pd.read_csv(path, keep_default_na=False, na_values=[""])',
    "filter_rows": 'df[df[column] > value]  (or ==, !=, >=, <, <=)',
    "group_agg": 'df.groupby(by, dropna=True)[column].agg(how)',
    "sort_rows": 'df.sort_values(column, ascending=True, kind="stable", na_position="last")',
    "drop_duplicates": 'df.drop_duplicates(subset=None, keep="first")',
    "value_counts": 'df[column].value_counts(dropna=True)',
}


def read_typed(path, types=TYPES, na_values=("",)):
    """Rows as dicts. A cell whose text is in na_values becomes None; other cells in a
    column listed in types are converted with that type; the rest stay text."""
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        row = {}
        for k, v in r.items():
            if v in na_values:
                row[k] = None
            elif k in types:
                row[k] = types[k](v)
            else:
                row[k] = v
        out.append(row)
    return out


def filter_rows(rows, column, op, value):
    """Rows where `row[column] op value` holds, the way pandas compares: a None cell is False
    for ==, >, >=, <, <= and True for != (NaN is not equal to anything)."""
    tests = {"==": lambda a: a == value, "!=": lambda a: a != value, ">": lambda a: a > value,
             ">=": lambda a: a >= value, "<": lambda a: a < value, "<=": lambda a: a <= value}
    if op not in tests:
        raise ValueError("op must be one of " + ", ".join(tests))
    return [r for r in rows if (op == "!=" if r[column] is None else tests[op](r[column]))]


def _sort_key_none_last(item):
    key = item[0]
    return (key is None, "" if key is None else key)


def group_agg(rows, by, column, how, dropna=True):
    """{group value: result}, groups sorted, a None group last. how is one of:
    "sum"   sum of non-None values; 0 when a group has none (pandas' min_count=0)
    "mean"  mean of non-None values; None when a group has none
    "count" how many non-None values
    "size"  how many rows, None or not
    dropna=True leaves out rows whose group value is None, as pandas does by default."""
    groups = {}
    for r in rows:
        key = r[by]
        if key is None and dropna:
            continue
        groups.setdefault(key, []).append(r[column])
    out = {}
    for key, values in sorted(groups.items(), key=_sort_key_none_last):
        present = [v for v in values if v is not None]
        if how == "sum":
            out[key] = sum(present) if present else 0
        elif how == "mean":
            out[key] = sum(present) / len(present) if present else None
        elif how == "count":
            out[key] = len(present)
        elif how == "size":
            out[key] = len(values)
        else:
            raise ValueError("how must be sum, mean, count or size")
    return out


def sort_rows(rows, column, ascending=True):
    """A stable sort on one column, with None last whichever way you sort."""
    present = [r for r in rows if r[column] is not None]
    missing = [r for r in rows if r[column] is None]
    return sorted(present, key=lambda r: r[column], reverse=not ascending) + missing


def drop_duplicates(rows, subset=None, keep="first"):
    """Rows whose values in subset (all columns when None) were not seen before.
    keep="first" keeps the first copy, "last" the last, False drops every copy. None equals None."""
    cols = subset or (list(rows[0]) if rows else [])
    keys = [tuple(r[c] for c in cols) for r in rows]
    counts = {}
    for k in keys:
        counts[k] = counts.get(k, 0) + 1
    if keep is False:
        return [r for r, k in zip(rows, keys) if counts[k] == 1]
    order = range(len(rows)) if keep == "first" else range(len(rows) - 1, -1, -1)
    seen, kept = set(), set()
    for i in order:
        if keys[i] not in seen:
            seen.add(keys[i])
            kept.add(i)
    return [r for i, r in enumerate(rows) if i in kept]


def value_counts(rows, column, dropna=True):
    """{value: rows with that value}, most common first (ties in order of first appearance).
    dropna=True leaves out None."""
    counts = {}
    for r in rows:
        v = r[column]
        if v is None and dropna:
            continue
        counts[v] = counts.get(v, 0) + 1
    first = {}
    for i, r in enumerate(rows):
        first.setdefault(r[column], i)
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], first[kv[0]])))


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
