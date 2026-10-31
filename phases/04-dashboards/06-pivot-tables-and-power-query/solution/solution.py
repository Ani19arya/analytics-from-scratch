"""Lesson 06: pivot tables and Power Query steps. Worked answer.

Run from the lesson folder: python3 solution/solution.py"""
import csv
import glob
import os
from datetime import datetime

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
HEADER_FIRST_CELL = "Receipt"
RENAMES = {"Qty": "Units", "Sales": "Revenue", "Store name": "Store"}
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%b %d, %Y"]   # slash dates in these exports are day first
COLUMNS = ["Receipt", "Date", "Month", "Store", "Product", "Units", "Revenue"]


def read_raw(path):
    """One file as a list of rows, each a list of text cells (Power Query: Source)."""
    with open(path, newline="") as f:
        return [row for row in csv.reader(f)]


# ---- the steps, in order. Each takes the table from the step before and returns a new one.

def removed_top_rows(raw):
    """Skip every line above the header, found by a rule (its first cell is Receipt), not a count."""
    for i, row in enumerate(raw):
        if row and row[0].strip() == HEADER_FIRST_CELL:
            return raw[i:]
    raise ValueError("no header row: no line starts with %r" % HEADER_FIRST_CELL)


def promoted_headers(raw):
    """First row becomes the column names. Short rows are padded with empty cells."""
    header = [h.strip() for h in raw[0]]
    return [dict(zip(header, row + [""] * (len(header) - len(row)))) for row in raw[1:]]


def renamed_columns(table, renames=RENAMES):
    """Give every month the same column names. A name that is not in this file is left alone."""
    return [{renames.get(k, k): v for k, v in row.items()} for row in table]


def trimmed_text(table):
    """Strip both ends of every cell and collapse inner runs of spaces."""
    return [{k: " ".join((v or "").split()) for k, v in row.items()} for row in table]


def capitalized_each_word(table, column="Store"):
    """'OLD TOWN' and 'old town' both become 'Old Town'."""
    return [dict(row, **{column: row[column].title()}) for row in table]


def filtered_rows(table):
    """Keep receipts only: drop blank lines and the Total line the export adds."""
    return [row for row in table if row.get("Receipt", "") not in ("", "Total")]


def parse_date(text):
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError("unreadable date %r" % text)


def parse_money(text):
    return float(text.replace("$", "").replace(",", ""))


def changed_type(table):
    """Date to YYYY-MM-DD, Units to a whole number, Revenue to a number. A bad cell raises ValueError."""
    out = []
    for row in table:
        try:
            out.append(dict(row, Date=parse_date(row["Date"]), Units=int(row["Units"]),
                            Revenue=parse_money(row["Revenue"])))
        except (KeyError, ValueError) as e:
            raise ValueError("receipt %s: %s" % (row.get("Receipt"), e))
    return out


def removed_duplicates(table, key="Receipt"):
    """Keep the first row of each receipt."""
    seen, out = set(), []
    for row in table:
        if row[key] not in seen:
            seen.add(row[key])
            out.append(row)
    return out


def added_custom(table):
    """Add Month (YYYY-MM) and put the columns in one fixed order."""
    return [{c: (row["Date"][:7] if c == "Month" else row.get(c)) for c in COLUMNS} for row in table]


STEPS = [
    ("Removed Top Rows", removed_top_rows),
    ("Promoted Headers", promoted_headers),
    ("Renamed Columns", renamed_columns),
    ("Trimmed Text", trimmed_text),
    ("Capitalized Each Word", capitalized_each_word),
    ("Filtered Rows", filtered_rows),
    ("Changed Type", changed_type),
    ("Removed Duplicates", removed_duplicates),
    ("Added Custom", added_custom),
]


def apply_steps(raw, steps=STEPS):
    """Run every step in order. Return (table, log) where log is [(step name, rows after it)]."""
    table, log = raw, []
    for name, step in steps:
        table = step(table)
        log.append((name, len(table)))
    return table, log


def appended(tables):
    """Table.Combine: stack the tables. A column missing from one table is None in its rows."""
    columns = []
    for t in tables:
        for row in t:
            for c in row:
                if c not in columns:
                    columns.append(c)
    return [{c: row.get(c) for c in columns} for t in tables for row in t]


def combine(tables):
    """Append the cleaned months, then remove repeated receipts (the same file appended twice)."""
    return removed_duplicates(appended(tables))


def pivot(rows, index="Store", columns="Month", values="Revenue"):
    """Sum of values by index (down the side) and columns (across the top). Returns a dict:
      rows, columns     sorted lists of the index and column values
      cells             {(row value, column value): sum}, rounded to 2 decimals
      row_totals, column_totals, grand_total
    A value that is not a number (None) is skipped. A combination with no numbers is left
    out of cells, so it shows as a blank, not a zero."""
    cells, row_totals, col_totals = {}, {}, {}
    for r in rows:
        v = r.get(values)
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            continue
        k = (r[index], r[columns])
        cells[k] = cells.get(k, 0) + v
        row_totals[r[index]] = row_totals.get(r[index], 0) + v
        col_totals[r[columns]] = col_totals.get(r[columns], 0) + v
    rnd = lambda d: {k: round(v, 2) for k, v in d.items()}
    return {"rows": sorted(row_totals), "columns": sorted(col_totals), "cells": rnd(cells),
            "row_totals": rnd(row_totals), "column_totals": rnd(col_totals),
            "grand_total": round(sum(row_totals.values()), 2)}


def refresh(data_dir=DATA, pattern="sales_*.csv"):
    """The one click: every monthly file in the folder, through the same steps, appended."""
    tables = [apply_steps(read_raw(p))[0] for p in sorted(glob.glob(os.path.join(data_dir, pattern)))]
    return combine(tables)


def render_pivot(p, fmt="{:,.2f}"):
    """A plain text pivot table with totals."""
    head = ["Store"] + p["columns"] + ["Total"]
    lines = [head]
    for r in p["rows"]:
        lines.append([r] + [fmt.format(p["cells"][(r, c)]) if (r, c) in p["cells"] else "" for c in p["columns"]]
                     + [fmt.format(p["row_totals"][r])])
    lines.append(["Total"] + [fmt.format(p["column_totals"][c]) for c in p["columns"]]
                 + [fmt.format(p["grand_total"])])
    widths = [max(len(line[i]) for line in lines) for i in range(len(head))]
    return "\n".join("  ".join(cell.ljust(w) if i == 0 else cell.rjust(w) for i, (cell, w) in
                               enumerate(zip(line, widths))) for line in lines)


def main():
    for path in sorted(glob.glob(os.path.join(DATA, "sales_*.csv"))):
        _, log = apply_steps(read_raw(path))
        print(os.path.basename(path), log)
    print(render_pivot(pivot(refresh())))


if __name__ == "__main__":
    main()
