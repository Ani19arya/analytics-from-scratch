"""Lesson 09 solution: data quality tests as code, run on every nightly load.

Run: python3 solution/solution.py   (replays the last two weeks of loads through the checks)
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

def check_not_null(rows, column):
    """Row numbers (0-based) where column is blank."""
    return [i for i, r in enumerate(rows) if blank(r.get(column))]


def check_unique(rows, column):
    """Sorted values that appear on more than one row. Blanks are not_null's job: skipped."""
    seen, dupes = set(), set()
    for r in rows:
        v = r.get(column)
        if blank(v):
            continue
        if v in seen:
            dupes.add(v)
        seen.add(v)
    return sorted(dupes)


def check_accepted_values(rows, column, allowed):
    """Row numbers whose non-blank value is not in allowed (exact match, case counts)."""
    return [i for i, r in enumerate(rows) if not blank(r.get(column)) and r[column] not in allowed]


def check_range(rows, column, lo, hi):
    """Row numbers whose non-blank value is not a number, or is outside lo..hi (both included)."""
    bad = []
    for i, r in enumerate(rows):
        v = r.get(column)
        if blank(v):
            continue
        try:
            x = float(v)
        except ValueError:
            bad.append(i)
            continue
        if not lo <= x <= hi:
            bad.append(i)
    return bad


def check_relationships(rows, column, keys):
    """Row numbers whose non-blank value is not one of keys (like a foreign key)."""
    keys = set(keys)
    return [i for i, r in enumerate(rows) if not blank(r.get(column)) and r[column] not in keys]


def check_vs_history(value, history, tolerance=TOLERANCE, window=WINDOW, min_history=MIN_HISTORY):
    """Compare today's value with the median of the last `window` values in history.
    [] if it is within median * (1 - tolerance) .. median * (1 + tolerance), or if there are
    fewer than min_history values to judge by. Otherwise [(value, low, high)]."""
    recent = list(history)[-window:]
    if len(recent) < min_history:
        return []
    mid = statistics.median(recent)
    low, high = round(mid * (1 - tolerance), 2), round(mid * (1 + tolerance), 2)
    return [] if low <= value <= high else [(value, low, high)]


def run_suite(rows, suite):
    """One result per check, in suite order:
    {"name", "severity", "status": "pass" | "warn" | "fail", "failures": count, "sample": first 3}.
    A failing check is "fail" if its severity is "error" and "warn" if it is "warn"."""
    results = []
    for name, severity, check in suite:
        found = list(check(rows))
        if not found:
            status = "pass"
        else:
            status = "fail" if severity == "error" else "warn"
        results.append({"name": name, "severity": severity, "status": status,
                        "failures": len(found), "sample": found[:3]})
    return results


def gate(results):
    """Raise LoadRejected naming every failed error check. Warnings never stop a load."""
    failed = [r["name"] for r in results if r["status"] == "fail"]
    if failed:
        raise LoadRejected("load rejected: " + ", ".join(failed))


def replay(rows, customers):
    """Run the suite on every load in date order, as the nightly job would have.
    Only loads that pass the gate go into the history the next loads are compared with.
    Returns {load_date: results}."""
    ids = {c["customer_id"] for c in customers}
    history = {"rows": [], "revenue": []}
    out = {}
    for day, load in split_loads(rows).items():
        results = run_suite(load, default_suite(ids, history))
        out[day] = results
        try:
            gate(results)
        except LoadRejected:
            continue
        history["rows"].append(len(load))
        history["revenue"].append(revenue(load))
    return out


def main():
    rows, customers = load_csv("orders.csv"), load_csv("customers.csv")
    for day, results in replay(rows, customers).items():
        failed = [r["name"] for r in results if r["status"] == "fail"]
        warned = [r["name"] for r in results if r["status"] == "warn"]
        verdict = "REJECT" if failed else "ok"
        print("%s %-6s %s" % (day, verdict, "; ".join(failed + ["warn: " + w for w in warned])))


if __name__ == "__main__":
    main()
