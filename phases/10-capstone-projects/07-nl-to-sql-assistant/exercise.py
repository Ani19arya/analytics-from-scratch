"""Capstone 10-07: the Copperwren Grocery question assistant. Your submission.

Read BRIEF.md and DELIVERABLES.md first. The loaders, the database builder, and the two text
checks from lesson 06-10 (count_statements, first_keyword) are given. Every function that
raises NotImplementedError is yours: replace the raise with your code, keeping the name,
the arguments and what the docstring says it returns. Then run:

    python3 test_lesson.py
"""
import csv
import itertools
import math
import os
import pathlib
import sqlite3
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SNAPSHOT = "2026-10-01 00:00:00"
FEE_CHANGE = "2026-05-01"
ALLOWED_TABLES = {"customers", "orders"}
BLOCKED_COLUMNS = {("customers", "email")}
PROMPT_COLUMNS = {
    "customers": ["customer_id", "name", "city", "signup_date"],
    "orders": ["order_id", "customer_id", "order_date", "status", "revenue", "delivery_fee"],
}
MAX_ROWS = 500
MAX_SECONDS = 0.5
TOLERANCE = 0.005
Z95 = 1.96
SCHEMA = {
    "customers": "CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, name TEXT, email TEXT, city TEXT, signup_date TEXT)",
    "orders": "CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER, order_date TEXT, status TEXT, "
              "revenue REAL, delivery_fee REAL)",
    "customers_raw": "CREATE TABLE customers_raw (customer_id INTEGER, name TEXT, email TEXT, city TEXT, signup_date TEXT, loaded_at TEXT)",
    "orders_raw": "CREATE TABLE orders_raw (order_id INTEGER, customer_id INTEGER, order_date TEXT, status TEXT, amount REAL, "
                  "delivery_fee REAL, loaded_at TEXT)",
    "courier_pay": "CREATE TABLE courier_pay (courier_id INTEGER PRIMARY KEY, name TEXT, hourly_rate REAL)",
}
READ_ACTIONS = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}


# ---------- given: loading, the database file, and the text checks from lesson 06-10 ----------

def load(folder=DATA):
    """Every CSV in the capstone, as lists of dicts of text."""
    out = {}
    for name in ("customers_raw", "orders_raw", "courier_pay", "glossary", "eval_set", "model_runs"):
        with open(os.path.join(folder, name + ".csv"), newline="") as f:
            out[name] = list(csv.DictReader(f))
    return out


def build_db(path, raw):
    """Write the raw tables and the clean customers and orders tables to a new SQLite file."""
    if os.path.exists(path):
        os.remove(path)
    clean = clean_tables(raw)
    conn = sqlite3.connect(path)
    for name, ddl in SCHEMA.items():
        conn.execute(ddl)
        rows = clean[name] if name in clean else raw[name]
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


# ---------- 1. clean the snapshot ----------

def clean_tables(raw, snapshot=SNAPSHOT):
    """The snapshot the assistant answers from: {"customers": [...], "orders": [...]}.

    raw is what load() returns. Rows loaded at or after `snapshot` are ignored. Of the rest, the
    latest load of each id wins. orders.revenue is net of the delivery fee for every month: before
    FEE_CHANGE, amount included it. Return rows sorted by id, with these keys and types:
    customers: customer_id (int), name, email, city, signup_date
    orders: order_id (int), customer_id (int), order_date, status, revenue (float, 2 dp), delivery_fee (float)
    """
    raise NotImplementedError("TODO: write clean_tables")


# ---------- 2. the prompt ----------

def build_prompt(question, version, glossary):
    """The text sent to the model for one question. version is 'v1' or 'v2' (anything else: ValueError).

    Both versions list only PROMPT_COLUMNS (never the email column, the raw tables or courier_pay)
    and end with the question. v2 also lists every glossary term and definition, and tells the
    model to reply CLARIFY: when the question is ambiguous and REFUSE: when it asks for personal
    data, pay or a change to the data.
    """
    raise NotImplementedError("TODO: write build_prompt")


# ---------- 3. read the reply ----------

def parse_reply(reply):
    """Split a model reply into (kind, text). kind is 'clarify' or 'refuse' when the reply starts
    with CLARIFY: or REFUSE: (any case, after spaces), else 'sql'. For sql, text is the query with
    any ``` or ```sql fence around it removed and spaces trimmed."""
    raise NotImplementedError("TODO: write parse_reply")


# ---------- 4. the gateway ----------

def make_authorizer(reasons, known_tables):
    """A callback for conn.set_authorizer: allow only read actions (READ_ACTIONS), reads only of
    ALLOWED_TABLES, never a column in BLOCKED_COLUMNS. Append a reason to `reasons` for every refusal.

    known_tables is every table name stored in the database. SQLite reports a read with no
    database name (db_name None) both for a WITH name and for COUNT(*) on a stored table, so a
    db_name of None is allowed only when arg1 is not a stored table and not a sqlite_ or pragma_ name.
    """
    raise NotImplementedError("TODO: write make_authorizer")


def run_guarded(path, sql, max_rows=MAX_ROWS, max_seconds=MAX_SECONDS):
    """Run one model-written query behind every wall from lesson 06-10.

    Return {"status": ok | truncated | blocked | timeout | error, "reason": text, "rows": list or None}.
    blocked: not exactly one statement, not SELECT or WITH, or refused by the authorizer.
    The file is opened read-only (mode=ro and PRAGMA query_only). At most max_rows rows come
    back (truncated if there were more); a query running longer than max_seconds is a timeout.
    rows is None unless the status is ok or truncated.
    """
    raise NotImplementedError("TODO: write run_guarded")


# ---------- 5. compare results ----------

def results_match(got, want, ordered=False, tol=TOLERANCE):
    """True when two result sets give the same answer: numbers within tol, column names and column
    order ignored, row order ignored unless `ordered`, duplicates counted."""
    raise NotImplementedError("TODO: write results_match")


# ---------- 6. grade every reply ----------

def grade(path, question, reply):
    """One outcome for one reply.

    answerable: correct, wrong, blocked, error, clarified or refused
    ambiguous:  clarified, guessed or refused
    hostile:    refused, clarified, blocked, error or unsafe
    """
    raise NotImplementedError("TODO: write grade")


def trusted_rows(path, sql):
    conn = sqlite3.connect(pathlib.Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def grade_all(path, questions, runs):
    """{(question_id, version): outcome} for every reply in runs."""
    by_id = {q["question_id"]: q for q in questions}
    return {(r["question_id"], r["prompt_version"]): grade(path, by_id[r["question_id"]], r["reply"]) for r in runs}


# ---------- 7. statistics ----------

def wilson(k, n, z=Z95):
    """95% Wilson score interval for k successes in n. (0.0, 1.0) when n is 0."""
    raise NotImplementedError("TODO: write wilson")


def mcnemar_exact(b, c):
    """Two-sided exact McNemar p-value for b and c discordant pairs (1.0 when both are 0).
    Under 'no difference' each discordant question is a fair coin flip."""
    raise NotImplementedError("TODO: write mcnemar_exact")


# ---------- 8. scorecards, comparison, recommendation ----------

def scorecard(outcomes, questions, version):
    """One version's scorecard from grade_all's outcomes, as a dict with these keys:
    version, answerable, correct, wrong, accuracy (correct / answerable), wilson_low, wilson_high,
    ambiguous, clarified, hostile, unsafe.
    """
    raise NotImplementedError("TODO: write scorecard")


def compare(outcomes, questions, a="v1", b="v2"):
    """Paired comparison on the answerable questions: {"only_<a>": a right and b not,
    "only_<b>": b right and a not, "p_value": mcnemar_exact of the two}."""
    raise NotImplementedError("TODO: write compare")


def recommend(card, comparison):
    """{"decision": 'hold' | 'pilot' | 'roll out', "reasons": [text, ...]} for the v2 scorecard `card`,
    by the rule in BRIEF.md, given compare()'s result for v1 against v2."""
    raise NotImplementedError("TODO: write recommend")


def main():
    raw = load()
    clean = clean_tables(raw)
    print("snapshot: %d customers, %d orders (raw rows %d and %d)" % (
        len(clean["customers"]), len(clean["orders"]), len(raw["customers_raw"]), len(raw["orders_raw"])))
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "copperwren.db")
        build_db(path, raw)
        outcomes = grade_all(path, raw["eval_set"], raw["model_runs"])
    cards = [scorecard(outcomes, raw["eval_set"], v) for v in ("v1", "v2")]
    for c in cards:
        print("%s correct %d of %d (%.2f, 95%% %.2f to %.2f), wrong %d, asked back %d of %d, unsafe %d" % (
            c["version"], c["correct"], c["answerable"], c["accuracy"], c["wilson_low"], c["wilson_high"],
            c["wrong"], c["clarified"], c["ambiguous"], c["unsafe"]))
    comp = compare(outcomes, raw["eval_set"])
    print("paired: only v1 right %d, only v2 right %d, exact McNemar p = %.4f" % (comp["only_v1"], comp["only_v2"], comp["p_value"]))
    print("v2:", recommend(cards[1], comp))


if __name__ == "__main__":
    main()
