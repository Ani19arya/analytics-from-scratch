"""Lesson 06: join two files and prove nothing was lost. Worked answer.

Run from the lesson folder: python3 solution/solution.py"""
import csv
import os

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
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
    index, cols = index_by(right, key), _right_columns(left, right, key)
    out = []
    for row in left:
        matches = [] if blank(row.get(key)) else index.get(row[key], [])
        for m in matches or [None]:
            merged = dict(row)
            for src, name in cols:
                merged[name] = m[src] if m is not None else None
            out.append(merged)
    return out


def inner_join(left, right, key):
    """Only left rows that match, each paired with every matching right row."""
    index, cols = index_by(right, key), _right_columns(left, right, key)
    out = []
    for row in left:
        for m in ([] if blank(row.get(key)) else index.get(row[key], [])):
            merged = dict(row)
            for src, name in cols:
                merged[name] = m[src]
            out.append(merged)
    return out


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
    index = index_by(right, key)
    left_keys = {r[key] for r in left if not blank(r.get(key))}
    blank_rows = [r for r in left if blank(r.get(key))]
    unmatched = [r for r in left if not blank(r.get(key)) and r[key] not in index]
    fan_rows = fan_amount = 0
    for r in left:
        n = len(index.get(r.get(key), [])) if not blank(r.get(key)) else 0
        if n > 1:
            fan_rows += n - 1
            fan_amount += (n - 1) * float(r[amount])
    rep = {"left_rows": len(left), "right_rows": len(right), "joined_rows": len(joined),
           "row_diff": len(joined) - len(left),
           "left_amount": _total(left, amount), "joined_amount": _total(joined, amount),
           "blank_key_rows": len(blank_rows),
           "unmatched_left_keys": sorted({r[key] for r in unmatched}),
           "unmatched_left_rows": len(blank_rows) + len(unmatched),
           "unmatched_left_amount": _total(blank_rows + unmatched, amount),
           "unmatched_right_keys": sorted(k for k in index if k not in left_keys),
           "duplicate_right_keys": sorted(k for k, rows in index.items() if len(rows) > 1),
           "fanout_rows": fan_rows, "fanout_amount": round(fan_amount, 2)}
    rep["amount_diff"] = round(rep["joined_amount"] - rep["left_amount"], 2)
    problems = []
    if rep["row_diff"] > 0:
        problems.append("rows_added")
    if rep["row_diff"] < 0:
        problems.append("rows_lost")
    if rep["amount_diff"] != 0:
        problems.append("amount_changed")
    if rep["unmatched_left_rows"]:
        problems.append("unmatched_left")
    rep["problems"], rep["ok"] = problems, not problems
    return rep


def assert_reconciled(report, allow=()):
    """Stop the pipeline unless every problem in the report is in allow.
    Raises ValueError naming the problems, so a bad join can never reach a report."""
    bad = [p for p in report["problems"] if p not in allow]
    if bad:
        raise ValueError("join failed reconciliation: %s (rows %d -> %d, amount %.2f -> %.2f)" % (
            ", ".join(bad), report["left_rows"], report["joined_rows"], report["left_amount"],
            report["joined_amount"]))


def clean_catalogue(products, key="sku", field="category"):
    """One row per sku: [{key: sku, field: category}], sorted by sku. Exact repeats collapse
    to one row. A sku listed with two different categories gets NEEDS_REVIEW, so the join
    cannot fan out and the disagreement stays visible."""
    seen = {}
    for p in products:
        if not blank(p.get(key)):
            seen.setdefault(p[key], set()).add(p[field])
    return [{key: k, field: (next(iter(v)) if len(v) == 1 else NEEDS_REVIEW)} for k, v in sorted(seen.items())]


def revenue_by_category(joined, key="sku", amount="amount", field="category"):
    """Sum amount by category over a joined table. A line with no category goes to NO_KEY if
    its key is blank and to UNMATCHED otherwise, so every line lands in exactly one bucket."""
    out = {}
    for row in joined:
        bucket = row.get(field)
        if bucket is None:
            bucket = NO_KEY if blank(row.get(key)) else UNMATCHED
        out[bucket] = out.get(bucket, 0.0) + float(row[amount])
    return {k: round(v, 2) for k, v in sorted(out.items())}


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
