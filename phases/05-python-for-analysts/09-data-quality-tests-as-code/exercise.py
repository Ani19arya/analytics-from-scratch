"""Lesson 09: data quality tests as code. Your turn.

load_csv, blank, split_loads, revenue, default_suite and LoadRejected are done for you.
Write every function below "the lesson" that raises NotImplementedError.
Run from this folder: python3 test_lesson.py
"""
import csv
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
STATUSES = {"paid", "refunded", "cancelled"}
WINDOW, MIN_HISTORY, TOLERANCE = 7, 3, 0.5


# ---- done for you ---------------------------------------------------------------

def load_csv(name, data_dir=DATA):
    with open(os.path.join(data_dir, name), newline="") as f:
        return list(csv.DictReader(f))


def blank(value):
    """None, or empty after stripping spaces: what a CSV gives for NULL."""
    return value is None or str(value).strip() == ""


def split_loads(rows):
    """{load_date: [rows of that load]}, oldest load first."""
    loads = {}
    for r in rows:
        loads.setdefault(r["load_date"], []).append(r)
    return dict(sorted(loads.items()))


def revenue(rows):
    """Sum of amount over rows whose amount is a number."""
    total = 0.0
    for r in rows:
        try:
            total += float(r["amount"])
        except (TypeError, ValueError):
            pass
    return round(total, 2)


def default_suite(customer_ids, history):
    """The checks every nightly load must pass: (name, severity, function of the rows).
    history is {"rows": [...], "revenue": [...]} from earlier loads that passed."""
    return [
        ("order_id not null", "error", lambda rows: check_not_null(rows, "order_id")),
        ("order_id unique", "error", lambda rows: check_unique(rows, "order_id")),
        ("currency not null", "error", lambda rows: check_not_null(rows, "currency")),
        ("status accepted values", "error", lambda rows: check_accepted_values(rows, "status", STATUSES)),
        ("amount between 0 and 5000", "error", lambda rows: check_range(rows, "amount", 0, 5000)),
        ("customer_id in customers", "warn", lambda rows: check_relationships(rows, "customer_id", customer_ids)),
        ("row count near recent median", "error",
         lambda rows: check_vs_history(len(rows), history["rows"], TOLERANCE)),
        ("revenue near recent median", "error",
         lambda rows: check_vs_history(revenue(rows), history["revenue"], TOLERANCE)),
    ]


class LoadRejected(Exception):
    """Raised by gate() when a check with severity "error" fails."""


# ---- the lesson -----------------------------------------------------------------
# Each check returns a list of what broke the rule. An empty list means the check passed.

def check_not_null(rows, column):
    """Row numbers (0-based) where column is blank or missing."""
    # TODO
    raise NotImplementedError


def check_unique(rows, column):
    """Sorted values that appear on more than one row. Skip blanks: they are not_null's job."""
    # TODO
    raise NotImplementedError


def check_accepted_values(rows, column, allowed):
    """Row numbers whose non-blank value is not in allowed, matched exactly."""
    # TODO
    raise NotImplementedError


def check_range(rows, column, lo, hi):
    """Row numbers whose non-blank value is not a number, or is outside lo..hi (both included)."""
    # TODO
    raise NotImplementedError


def check_relationships(rows, column, keys):
    """Row numbers whose non-blank value is not one of keys."""
    # TODO
    raise NotImplementedError


def check_vs_history(value, history, tolerance=TOLERANCE, window=WINDOW, min_history=MIN_HISTORY):
    """Compare value with the median of the last `window` values of history.
    Pass ([]) inside median * (1 - tolerance) .. median * (1 + tolerance), both ends included
    and rounded to 2 decimals, or when there are fewer than min_history values.
    Fail: [(value, low, high)]."""
    # TODO
    raise NotImplementedError


def run_suite(rows, suite):
    """One dict per (name, severity, check) in suite, in order:
    {"name", "severity", "status": "pass" | "warn" | "fail", "failures": how many, "sample": the first 3}."""
    # TODO
    raise NotImplementedError


def gate(results):
    """Raise LoadRejected, naming every check whose status is "fail". Warnings never stop a load."""
    # TODO
    raise NotImplementedError


def replay(rows, customers):
    """Run default_suite on every load, oldest first, as the nightly job would have, and
    return {load_date: results}. Decide carefully which loads go into the history."""
    # TODO
    raise NotImplementedError


def main():
    rows, customers = load_csv("orders.csv"), load_csv("customers.csv")
    for day, results in replay(rows, customers).items():
        failed = [r["name"] for r in results if r["status"] == "fail"]
        warned = [r["name"] for r in results if r["status"] == "warn"]
        verdict = "REJECT" if failed else "ok"
        print("%s %-6s %s" % (day, verdict, "; ".join(failed + ["warn: " + w for w in warned])))


if __name__ == "__main__":
    main()
