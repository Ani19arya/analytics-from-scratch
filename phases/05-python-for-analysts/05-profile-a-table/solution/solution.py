"""Lesson 05: profile a table before you trust it. Worked answer.

Run from the lesson folder: python3 solution/solution.py"""
import csv
import os
import re
from datetime import date

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

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
    if value is None or value.strip() == "":
        return "empty"
    v = value.strip()
    if v.lower() in NULL_TOKENS:
        return "null_text"
    if INT.match(v):
        return "int"
    if FLOAT.match(v):
        return "float"
    if re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        try:
            date.fromisoformat(v)
            return "date"
        except ValueError:
            return "text"
    return "text"


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
    kinds = [classify(v) for v in values]
    present = [(v, FAMILY[k]) for v, k in zip(values, kinds) if k not in ("empty", "null_text")]
    types = {}
    for _, fam in present:
        types[fam] = types.get(fam, 0) + 1
    main = None
    if types:
        main = max(FAMILY_ORDER, key=lambda f: (types.get(f, 0), -FAMILY_ORDER.index(f)))
    main_values = [_typed(v, f) for v, f in present if f == main]
    empty, null_text = kinds.count("empty"), kinds.count("null_text")
    n = len(values)
    return {"count": n, "empty": empty, "null_text": null_text, "nulls": empty + null_text,
            "null_pct": round(100.0 * (empty + null_text) / n, 1) if n else 0.0,
            "distinct": len({v for v, _ in present}), "types": types, "main_type": main,
            "mixed": len(types) > 1,
            "min": min(main_values) if main_values else None, "max": max(main_values) if main_values else None}


def profile_table(rows, key=KEY):
    """Profile every column, plus the key. Returns rows, columns ({name: profile_column}),
    null_keys, distinct_keys, duplicate_keys (sorted keys seen more than once),
    duplicate_key_rows (rows with a key minus distinct keys) and exact_duplicate_rows
    (rows minus distinct whole rows)."""
    columns = list(rows[0]) if rows else []
    keys = [r.get(key) for r in rows]
    present = [k for k in keys if classify(k) not in ("empty", "null_text")]
    counts = {}
    for k in present:
        counts[k] = counts.get(k, 0) + 1
    return {"rows": len(rows), "columns": {c: profile_column([r.get(c) for r in rows]) for c in columns},
            "null_keys": len(keys) - len(present), "distinct_keys": len(counts),
            "duplicate_keys": sorted(k for k, n in counts.items() if n > 1),
            "duplicate_key_rows": len(present) - len(counts),
            "exact_duplicate_rows": len(rows) - len({tuple(sorted(r.items())) for r in rows})}


def out_of_range(values, low, high):
    """Count values of the same family as low (number or date) that fall outside [low, high].
    Empty, null and other-type cells are not counted here: they are counted elsewhere."""
    family = "number" if isinstance(low, (int, float)) else "date"
    n = 0
    for v in values:
        k = classify(v)
        if k in ("empty", "null_text") or FAMILY[k] != family:
            continue
        x = _typed(v, family)
        if x < low or x > high:
            n += 1
    return n


def check_fitness(rows, key=KEY, required=REQUIRED, rules=RULES):
    """Is the table fit for the board number? Returns (fit, reasons, profile).
    reasons is a list of (problem, column, count), in this order:
      ("no_rows", None, 0) alone, if there are no rows;
      ("duplicate_keys", key, duplicate_key_rows);
      then for each column in table order: ("missing", col, nulls) for a required column,
      ("mixed_types", col, cells not of the main type), ("out_of_range", col, count) for a rule.
    fit is True only when there are no reasons."""
    profile = profile_table(rows, key)
    if not rows:
        return False, [("no_rows", None, 0)], profile
    reasons = []
    if profile["duplicate_key_rows"]:
        reasons.append(("duplicate_keys", key, profile["duplicate_key_rows"]))
    for col, p in profile["columns"].items():
        if col in required and p["nulls"]:
            reasons.append(("missing", col, p["nulls"]))
        if p["mixed"]:
            reasons.append(("mixed_types", col, sum(p["types"].values()) - p["types"][p["main_type"]]))
        if col in rules:
            bad = out_of_range([r.get(col) for r in rows], *rules[col])
            if bad:
                reasons.append(("out_of_range", col, bad))
    return not reasons, reasons, profile


def is_paid_number(row, amount="amount"):
    return row.get("status") == "paid" and FAMILY.get(classify(row.get(amount))) == "number"


def naive_revenue(rows, amount="amount"):
    """What a quick SUM gives: the amount of every paid row whose amount reads as a number."""
    return round(sum(float(r[amount]) for r in rows if is_paid_number(r, amount)), 2)


def duplicate_inflation(rows, key=KEY, amount="amount"):
    """How much of naive_revenue comes from repeated keys: the amounts on every paid row
    after the first row for its key (numbers only; rows with no key are skipped)."""
    seen, extra = set(), 0.0
    for r in rows:
        k = r.get(key)
        if classify(k) in ("empty", "null_text"):
            continue
        if k in seen and is_paid_number(r, amount):
            extra += float(r[amount])
        seen.add(k)
    return round(extra, 2)


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
