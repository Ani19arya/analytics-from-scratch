"""Capstone 10-08: the Bramblequay Bikes analytics copilot. Your submission.

Read BRIEF.md and DELIVERABLES.md first. Loading, the database builder, the read-only gateway
from capstone 10-07 (run_guarded), sql_hash and parse_number are given. Every function that
raises NotImplementedError is yours: replace the raise with your code, keeping the name, the
arguments and what the docstring says it returns. Then run:

    python3 test_lesson.py
"""
import csv
import hashlib
import itertools
import json
import os
import pathlib
import re
import sqlite3
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SNAPSHOT = "2026-10-01 00:00:00"
MIN_MINUTES = 2
ALLOWED_TABLES = {"rentals", "stations", "station_events", "riders"}
BLOCKED_COLUMNS = {("riders", "email")}
MAX_ROWS = 500
MAX_SECONDS = 0.5
STEP_KINDS = {"query", "check", "recommend"}
SCHEMA = {
    "rentals": "CREATE TABLE rentals (rental_id INTEGER PRIMARY KEY, station_id TEXT, start_date TEXT, start_hour INTEGER, "
               "duration_min INTEGER, rider_type TEXT, rider_id INTEGER)",
    "rentals_raw": "CREATE TABLE rentals_raw (rental_id INTEGER, station_id TEXT, start_date TEXT, start_hour INTEGER, "
                   "duration_min INTEGER, rider_type TEXT, rider_id INTEGER, loaded_at TEXT)",
    "stations": "CREATE TABLE stations (station_id TEXT PRIMARY KEY, name TEXT, zone TEXT, docks INTEGER)",
    "station_events": "CREATE TABLE station_events (station_id TEXT, event TEXT, start_date TEXT, end_date TEXT, note TEXT)",
    "riders": "CREATE TABLE riders (rider_id INTEGER PRIMARY KEY, email TEXT, plan TEXT, signup_date TEXT)",
}
READ_ACTIONS = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}
NUMBER = re.compile(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?%?")


# ---------- given: loading, the database file and the read-only gateway (capstone 10-07) ----------

def load(folder=DATA):
    """Every file in data/: CSVs as lists of dicts of text, plan.json and draft.json parsed."""
    out = {}
    for name in ("stations", "station_events", "riders", "rentals_raw", "approvals"):
        with open(os.path.join(folder, name + ".csv"), newline="") as f:
            out[name] = list(csv.DictReader(f))
    for name in ("plan", "draft"):
        with open(os.path.join(folder, name + ".json")) as f:
            out[name] = json.load(f)
    return out


def build_db(path, data):
    """Write the raw tables and the clean rentals table to a new SQLite file at path."""
    if os.path.exists(path):
        os.remove(path)
    tables = dict(data, rentals=clean_rentals(data["rentals_raw"]))
    conn = sqlite3.connect(path)
    for name, ddl in SCHEMA.items():
        conn.execute(ddl)
        rows = tables[name]
        if rows:
            cols = list(rows[0].keys())
            conn.executemany("INSERT INTO %s (%s) VALUES (%s)" % (name, ", ".join(cols), ", ".join("?" * len(cols))),
                             [[r[c] for c in cols] for r in rows])
    conn.commit()
    conn.close()


def _skip(sql, i):
    """Index of the next character at or after i that is not whitespace or inside a comment."""
    n = len(sql)
    while i < n:
        if sql[i].isspace():
            i += 1
        elif sql.startswith("--", i):
            j = sql.find("\n", i)
            i = n if j == -1 else j + 1
        elif sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            i = n if j == -1 else j + 2
        else:
            return i
    return n


def count_statements(sql):
    """How many statements sql holds; a ; inside quotes or comments does not count."""
    count, has_code, i, n = 0, False, 0, len(sql)
    while i < n:
        j = _skip(sql, i)
        if j != i:
            i = j
            continue
        ch = sql[i]
        if ch in "'\"`[":
            close = "]" if ch == "[" else ch
            j = i + 1
            while True:
                j = sql.find(close, j)
                if j == -1 or close == "]" or not sql.startswith(close * 2, j):
                    break
                j += 2
            has_code, i = True, (n if j == -1 else j + 1)
            continue
        if ch == ";":
            count += 1 if has_code else 0
            has_code = False
        else:
            has_code = True
        i += 1
    return count + (1 if has_code else 0)


def first_keyword(sql):
    """The first word of sql in upper case, skipping whitespace and comments."""
    i = j = _skip(sql, 0)
    while j < len(sql) and (sql[j].isalpha() or sql[j] == "_"):
        j += 1
    return sql[i:j].upper()


def _authorizer(reasons, known_tables):
    known = {t.lower() for t in known_tables}

    def authorize(action, arg1, arg2, db_name, trigger):
        if action not in READ_ACTIONS:
            reasons.append("action %d is not allowed" % action)
            return sqlite3.SQLITE_DENY
        # SQLite passes the name as typed when no column is read: COUNT(*) FROM RENTALS_RAW gives "RENTALS_RAW"
        table = arg1.lower() if action == sqlite3.SQLITE_READ else None
        if action == sqlite3.SQLITE_READ and table not in ALLOWED_TABLES:
            # db_name is None for COUNT(*) on a WITH name, and also for COUNT(*) on a stored table
            if db_name is not None or table in known or table.startswith(("sqlite_", "pragma_")):
                reasons.append("table %s is not allowed" % arg1)
                return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_READ and (table, arg2) in BLOCKED_COLUMNS:
            reasons.append("column %s.%s is not allowed" % (arg1, arg2))
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    return authorize


def run_guarded(path, sql, max_rows=MAX_ROWS, max_seconds=MAX_SECONDS):
    """Run one query read-only behind an allowlist. Returns {"status": ok | truncated | blocked | timeout |
    error, "reason", "columns", "rows"}; rows are tuples, None unless the status is ok or truncated."""
    if count_statements(sql) != 1:
        return {"status": "blocked", "reason": "exactly one statement is allowed", "columns": None, "rows": None}
    if first_keyword(sql) not in ("SELECT", "WITH"):
        return {"status": "blocked", "reason": "only SELECT or WITH is allowed", "columns": None, "rows": None}
    conn = sqlite3.connect(pathlib.Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON")
    known = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")}
    reasons = []
    conn.set_authorizer(_authorizer(reasons, known))
    deadline = time.monotonic() + max_seconds
    conn.set_progress_handler(lambda: time.monotonic() > deadline, 1000)
    try:
        cur = conn.execute(sql)
        rows = cur.fetchmany(max_rows + 1)
        columns = [d[0] for d in cur.description]
    except sqlite3.Error as e:
        if reasons:
            return {"status": "blocked", "reason": "; ".join(sorted(set(reasons))), "columns": None, "rows": None}
        if "interrupted" in str(e):
            return {"status": "timeout", "reason": "took longer than %.1f seconds" % max_seconds, "columns": None, "rows": None}
        return {"status": "error", "reason": str(e), "columns": None, "rows": None}
    finally:
        conn.close()
    if len(rows) > max_rows:
        return {"status": "truncated", "reason": "more than %d rows" % max_rows, "columns": columns, "rows": rows[:max_rows]}
    return {"status": "ok", "reason": "", "columns": columns, "rows": rows}


def sql_hash(sql):
    """The audit fingerprint of the SQL that actually ran."""
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


# ---------- 1. the clean rentals table ----------

def clean_rentals(raw, snapshot=SNAPSHOT):
    """One row per rental_id: loads at or after `snapshot` ignored, the latest load of the rest wins,
    and only rentals of at least MIN_MINUTES minutes (from 16 August the app also logs false starts
    of 0 or 1 minute, which it used to drop). Rows sorted by rental_id, with keys
    rental_id (int), station_id, start_date, start_hour (int), duration_min (int), rider_type, rider_id (int)."""
    raise NotImplementedError("TODO: write clean_rentals")


# ---------- 2. the plan ----------

def validate_plan(plan):
    """Raise ValueError unless step ids are unique, kinds are query, check or recommend, a query has sql,
    a check names its check, and every dependency is an earlier step. Return the list of step ids."""
    raise NotImplementedError("TODO: write validate_plan")


# ---------- 3. the checks (code, not a model) ----------

def reconcile(total_rows, zone_rows, months=("2026-08", "2026-09")):
    """Do the zones add up to the totals? {"passed": bool, "diffs": {month: zone sum - total}}."""
    raise NotImplementedError("TODO: write reconcile")


def permutation_p(a, b):
    """Exact two-sided permutation p-value for the difference in means of a and b: the share of all
    ways to split the pooled values into groups of len(a) and len(b) whose difference is at least
    as large as the observed one. 1.0 if either list is empty."""
    raise NotImplementedError("TODO: write permutation_p")


def noise_check(daily_rows):
    """Daily counts (rows with start_date, month, rentals) split into August and September.
    {"passed": both months have days, "n_aug", "n_sep", "mean_aug", "mean_sep", "p_value"}."""
    raise NotImplementedError("TODO: write noise_check")


# ---------- 4. every number in the draft ----------

def parse_number(text):
    """'1,234' -> (1234.0, 0); '49.7%' -> (49.7, 1); '+2.2%' -> (2.2, 1). The second value is the decimals stated."""
    t = text.strip().rstrip("%").replace(",", "")
    decimals = len(t.split(".")[1]) if "." in t else 0
    return float(t), decimals


def check_claims(draft, results, status):
    """{"verdicts": {claim id: ok | mismatch | not_run | no_such_row | assumption}, "uncited": [number texts]}.

    A claim matches when it equals the cited value at the precision it states: within 0.5 x 10^-d
    for d decimals. kinds: value (one cell, expr 'col' or 'col / col'), count (rows matching where),
    pct_change ((to - from) / from x 100), pct_fall ((from - to) / from x 100), assumption.
    A step whose status is not 'done' cannot back a claim (not_run). Every number in the text that is
    not the text of some claim is uncited.
    """
    raise NotImplementedError("TODO: write check_claims")


def release(plan, status, results, report):
    """{"released": bool, "reasons": [...]}: release only if every check step ran and passed, every
    claim is ok or a labelled assumption, and no number is uncited."""
    raise NotImplementedError("TODO: write release")


# ---------- 5. the orchestrator ----------

def run_plan(plan, approvals, path, draft, max_steps=8):
    """Replay a copilot session with a human approving each step.

    Steps run in plan order (validate_plan first). For each step:
    - no approval record: status 'halted', and every later step 'not_reached';
    - decision 'reject': 'rejected'; 'edit' runs edited_sql instead (an edit with no SQL halts);
    - a dependency that is not 'done': 'skipped';
    - more than max_steps steps would run: 'halted' (budget), later steps 'not_reached';
    - query: run_guarded; 'done' if it returned rows, else 'blocked' or 'failed';
    - check: reconcile(first dependency, second) or noise_check(first dependency); always 'done';
    - recommend: check_claims and release on the draft; 'done'.
    The last approval record for a step counts. Results: query rows as dicts, a check as a one-item
    list, the recommend step as {"claims": ..., "release": ...}.
    Return {"status": {step: status}, "results": {step: result}, "log": [one dict per step in plan order:
    step, status, detail, sql_sha256 (of the SQL run, '' if none)]}.
    """
    raise NotImplementedError("TODO: write run_plan")


def main():
    data = load()
    rentals = clean_rentals(data["rentals_raw"])
    print("rentals: %d raw rows, %d clean" % (len(data["rentals_raw"]), len(rentals)))
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "bramblequay.db")
        build_db(path, data)
        run = run_plan(data["plan"], data["approvals"], path, data["draft"])
    for e in run["log"]:
        print("%s %-9s %s %s" % (e["step"], e["status"], e["sql_sha256"][:10], e["detail"]))
    print("S6", run["results"]["S6"][0])
    s7 = run["results"]["S7"][0]
    print("S7 mean Aug %.2f, mean Sep %.2f, p = %.4f" % (s7["mean_aug"], s7["mean_sep"], s7["p_value"]))
    final = run["results"]["S8"]
    print("claims", final["claims"]["verdicts"])
    print("release", final["release"])


if __name__ == "__main__":
    main()
