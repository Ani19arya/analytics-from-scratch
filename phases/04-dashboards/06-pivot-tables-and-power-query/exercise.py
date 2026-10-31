"""Lesson 06: pivot tables and Power Query steps. Your turn.

read_raw, parse_date, parse_money, capitalized_each_word, added_custom, STEPS,
render_pivot and main are done for you. Fill in every function that raises
NotImplementedError. Each step takes the table from the step before and returns a new
table; never refer to a row by its position in the file.
Run from this folder: python3 test_lesson.py"""
import csv
import glob
import os
from datetime import datetime

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
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
    # TODO: return raw from the first row whose first cell (stripped) is HEADER_FIRST_CELL; ValueError if none
    raise NotImplementedError


def promoted_headers(raw):
    """First row becomes the column names. Short rows are padded with empty cells."""
    # TODO: zip the header (raw[0]) with every later row, padding short rows with empty strings
    raise NotImplementedError


def renamed_columns(table, renames=RENAMES):
    """Give every month the same column names. A name that is not in this file is left alone."""
    # TODO: rebuild each row with renames.get(name, name) as the key
    raise NotImplementedError


def trimmed_text(table):
    """Strip both ends of every cell and collapse inner runs of spaces."""
    # TODO: strip and collapse spaces in every cell; a None cell becomes an empty string
    raise NotImplementedError


def capitalized_each_word(table, column="Store"):
    """'OLD TOWN' and 'old town' both become 'Old Town'."""
    return [dict(row, **{column: row[column].title()}) for row in table]


def filtered_rows(table):
    """Keep receipts only: drop blank lines and the Total line the export adds."""
    # TODO: keep rows whose Receipt is neither empty nor Total
    raise NotImplementedError


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
    # TODO: use parse_date, int and parse_money; turn any KeyError or ValueError into ValueError naming the receipt
    raise NotImplementedError


def removed_duplicates(table, key="Receipt"):
    """Keep the first row of each receipt."""
    # TODO: keep the first row for each value of key
    raise NotImplementedError


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
    # TODO: run each (name, step) in order, logging (name, len(table)) after each
    raise NotImplementedError


def appended(tables):
    """Table.Combine: stack the tables. A column missing from one table is None in its rows."""
    # TODO: collect every column name in order of first appearance, then rebuild every row with row.get(column)
    raise NotImplementedError


def combine(tables):
    """Append the cleaned months, then remove repeated receipts (the same file appended twice)."""
    # TODO: appended, then removed_duplicates
    raise NotImplementedError


def pivot(rows, index="Store", columns="Month", values="Revenue"):
    """Sum of values by index (down the side) and columns (across the top). Returns a dict:
      rows, columns     sorted lists of the index and column values
      cells             {(row value, column value): sum}, rounded to 2 decimals
      row_totals, column_totals, grand_total
    A value that is not a number (None) is skipped. A combination with no numbers is left
    out of cells, so it shows as a blank, not a zero."""
    # TODO: sum values per (index, columns) pair, per index and per column, skipping anything that is not a number
    raise NotImplementedError


def refresh(data_dir=DATA, pattern="sales_*.csv"):
    """The one click: every monthly file in the folder, through the same steps, appended."""
    # TODO: apply_steps to every file matching pattern in data_dir, in sorted name order, then combine
    raise NotImplementedError


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
