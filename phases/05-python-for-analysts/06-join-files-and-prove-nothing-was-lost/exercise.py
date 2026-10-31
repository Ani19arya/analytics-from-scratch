"""Lesson 06: join two files and prove nothing was lost. Your turn.

load_csv, blank, index_by, _right_columns, _total and main are done for you. Fill in every
function that raises NotImplementedError.
Run from this folder: python3 test_lesson.py"""
import csv
import os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
NO_KEY, UNMATCHED, NEEDS_REVIEW = "No SKU", "Unmatched", "Needs review"


def load_csv(name, data_dir=DATA):
    with open(os.path.join(data_dir, name), newline="") as f:
        return list(csv.DictReader(f))


def blank(value):
    """A key that can never match: None, or empty after stripping spaces (like NULL in SQL)."""
    return value is None or str(value).strip() == ""


def index_by(rows, key):
    """{key value: [rows with that value]}. Rows with a blank key are left out."""
    out = {}
    for r in rows:
        if not blank(r.get(key)):
            out.setdefault(r[key], []).append(r)
    return out


def _right_columns(left, right, key):
    """Right-hand column names to add, renamed to name_right if the left side already has them."""
    left_cols = set(left[0]) if left else set()
    cols = [c for c in (right[0] if right else {}) if c != key]
    return [(c, c + "_right" if c in left_cols else c) for c in cols]


def left_join(left, right, key):
    """Every left row, paired with EVERY right row whose key matches (so a key listed twice on
    the right gives two rows: a fan-out). A left row with no match, or a blank key, is kept
    once with the right-hand columns set to None. Left rows keep their order."""
    # TODO: for each left row, look up its matches with index_by (none for a blank key); emit one merged row per match, or one row with None for each right column
    raise NotImplementedError


def inner_join(left, right, key):
    """Only left rows that match, each paired with every matching right row."""
    # TODO: like left_join, but a left row with no match produces no row at all
    raise NotImplementedError


def _total(rows, amount):
    return round(sum(float(r[amount]) for r in rows if not blank(r.get(amount))), 2)


def reconcile(left, right, joined, key, amount):
    """Compare a join with its left input. Returns a dict:
      left_rows, right_rows, joined_rows, row_diff (joined - left)
      left_amount, joined_amount, amount_diff (joined - left), all rounded to cents
      blank_key_rows       left rows whose key is blank
      unmatched_left_keys  sorted keys on the left with no row on the right
      unmatched_left_rows, unmatched_left_amount   left rows with a blank or unmatched key
      unmatched_right_keys sorted keys on the right that no left row uses
      duplicate_right_keys sorted keys listed more than once on the right
      fanout_rows, fanout_amount   extra copies of left rows created by duplicate right keys
      problems             list of 'rows_added', 'rows_lost', 'amount_changed', 'unmatched_left'
      ok                   True when problems is empty"""
    # TODO: count rows and amounts on both sides, find unmatched and duplicate keys, count the fan-out, then list the problems
    raise NotImplementedError


def assert_reconciled(report, allow=()):
    """Stop the pipeline unless every problem in the report is in allow.
    Raises ValueError naming the problems, so a bad join can never reach a report."""
    # TODO: raise ValueError if any problem in report['problems'] is not in allow
    raise NotImplementedError


def clean_catalogue(products, key="sku", field="category"):
    """One row per sku: [{key: sku, field: category}], sorted by sku. Exact repeats collapse
    to one row. A sku listed with two different categories gets NEEDS_REVIEW, so the join
    cannot fan out and the disagreement stays visible."""
    # TODO: collect the set of categories per sku; one category keeps it, two or more become NEEDS_REVIEW
    raise NotImplementedError


def revenue_by_category(joined, key="sku", amount="amount", field="category"):
    """Sum amount by category over a joined table. A line with no category goes to NO_KEY if
    its key is blank and to UNMATCHED otherwise, so every line lands in exactly one bucket."""
    # TODO: add each row's amount to its category, or to NO_KEY or UNMATCHED when the category is None
    raise NotImplementedError


def main():
    lines, products = load_csv("order_lines.csv"), load_csv("products.csv")
    joined = left_join(lines, products, "sku")
    rep = reconcile(lines, products, joined, "sku", "amount")
    for k, v in rep.items():
        print("%-22s %s" % (k, v))
    catalogue = clean_catalogue(products)
    fixed = left_join(lines, catalogue, "sku")
    rep = reconcile(lines, catalogue, fixed, "sku", "amount")
    assert_reconciled(rep, allow=("unmatched_left",))
    print("after clean_catalogue:", rep["problems"], rep["joined_rows"], "rows", rep["joined_amount"])
    totals = revenue_by_category(fixed)
    print(totals)
    print("buckets add up to:", round(sum(totals.values()), 2), " order lines:", rep["left_amount"])


if __name__ == "__main__":
    main()
