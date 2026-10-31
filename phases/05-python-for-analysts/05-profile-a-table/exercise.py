"""Lesson 05: profile a table before you trust it. Your turn.

load_csv, the constants, is_paid_number and main are done for you. Fill in every
function that raises NotImplementedError.
Run from this folder: python3 test_lesson.py"""
import csv
import os
import re
from datetime import date

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Text that means "no value" in this export. "NA" is NOT here: in the country column it is Namibia.
NULL_TOKENS = ("null", "none", "n/a", "\\n")
FAMILY = {"int": "number", "float": "number", "date": "date", "text": "text"}
FAMILY_ORDER = ("number", "date", "text")      # breaks a tie for the main type
INT = re.compile(r"^-?\d+$")
FLOAT = re.compile(r"^-?\d+\.\d+$")

# What the board number needs from this table.
KEY = "payment_id"
REQUIRED = ["payment_id", "customer_id", "paid_at", "plan", "amount", "status"]
RULES = {"amount": (1.0, 1000.0), "paid_at": ("2026-07-01", "2026-09-30")}


def load_csv(name="payments.csv", data_dir=DATA):
    with open(os.path.join(data_dir, name), newline="") as f:
        return list(csv.DictReader(f))


def classify(value):
    """'empty', 'null_text', 'int', 'float', 'date' or 'text' for one cell.
    None and whitespace-only cells are empty. NULL_TOKENS (any case) are null_text."""
    # TODO: empty first (None or only spaces), then NULL_TOKENS (lowercase, stripped), then INT, FLOAT, a real YYYY-MM-DD date, else text
    raise NotImplementedError


def _typed(value, family):
    v = value.strip()
    return float(v) if family == "number" else v


def profile_column(values):
    """Profile one column given as a list of cells (text or None). Returns:
    count, empty, null_text, nulls, null_pct (one decimal, 0.0 for no rows),
    distinct (different non-null values, compared exactly as written),
    types ({family: count} over non-null cells), main_type (most common family, None if
    no values), mixed (more than one family), min and max (over values of the main type:
    numbers as floats, dates and text as text; None if no values)."""
    # TODO: classify every cell, count the families of the non-null ones, then fill in every key listed above
    raise NotImplementedError


def profile_table(rows, key=KEY):
    """Profile every column, plus the key. Returns rows, columns ({name: profile_column}),
    null_keys, distinct_keys, duplicate_keys (sorted keys seen more than once),
    duplicate_key_rows (rows with a key minus distinct keys) and exact_duplicate_rows
    (rows minus distinct whole rows)."""
    # TODO: profile_column for each column of rows[0], then count keys that are not null
    raise NotImplementedError


def out_of_range(values, low, high):
    """Count values of the same family as low (number or date) that fall outside [low, high].
    Empty, null and other-type cells are not counted here: they are counted elsewhere."""
    # TODO: skip nulls and cells of another family; count the rest that are below low or above high
    raise NotImplementedError


def check_fitness(rows, key=KEY, required=REQUIRED, rules=RULES):
    """Is the table fit for the board number? Returns (fit, reasons, profile).
    reasons is a list of (problem, column, count), in this order:
      ("no_rows", None, 0) alone, if there are no rows;
      ("duplicate_keys", key, duplicate_key_rows);
      then for each column in table order: ("missing", col, nulls) for a required column,
      ("mixed_types", col, cells not of the main type), ("out_of_range", col, count) for a rule.
    fit is True only when there are no reasons."""
    # TODO: profile_table, then build the reasons in the order above
    raise NotImplementedError


def is_paid_number(row, amount="amount"):
    return row.get("status") == "paid" and FAMILY.get(classify(row.get(amount))) == "number"


def naive_revenue(rows, amount="amount"):
    """What a quick SUM gives: the amount of every paid row whose amount reads as a number."""
    # TODO: sum float(amount) over rows where is_paid_number(row)
    raise NotImplementedError


def duplicate_inflation(rows, key=KEY, amount="amount"):
    """How much of naive_revenue comes from repeated keys: the amounts on every paid row
    after the first row for its key (numbers only; rows with no key are skipped)."""
    # TODO: walk the rows, remember each key; add the paid amount of any row whose key you have already seen
    raise NotImplementedError


def main():
    rows = load_csv()
    fit, reasons, profile = check_fitness(rows)
    print("rows:", profile["rows"], " distinct keys:", profile["distinct_keys"],
          " repeated keys:", profile["duplicate_keys"])
    print("%-12s %5s %5s %5s %8s  %-28s %s" % ("column", "nulls", "empty", "text", "distinct", "types", "min .. max"))
    for col, p in profile["columns"].items():
        print("%-12s %5d %5d %5d %8d  %-28s %s .. %s" % (col, p["nulls"], p["empty"], p["null_text"], p["distinct"],
                                                        p["types"], p["min"], p["max"]))
    print("fit for the board number:", fit)
    for r in reasons:
        print("  ", r)
    print("naive revenue:", naive_revenue(rows), " of which repeated keys:", duplicate_inflation(rows))


if __name__ == "__main__":
    main()
