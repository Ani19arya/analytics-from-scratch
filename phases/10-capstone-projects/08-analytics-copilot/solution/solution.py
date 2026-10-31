"""Capstone 10-08: the Bramblequay Bikes analytics copilot. Worked solution.

Read solution/WRITEUP.md for the reasoning and the one-page write-up. Run from the capstone
folder to replay the recorded session and print the audit log:

    python3 solution/solution.py
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

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    best = {}
    for r in raw:
        if r["loaded_at"] >= snapshot:
            continue
        k = int(r["rental_id"])
        if k not in best or r["loaded_at"] > best[k]["loaded_at"]:
            best[k] = r
    out = []
    for k in sorted(best):
        r = best[k]
        if int(r["duration_min"]) < MIN_MINUTES:
            continue
        out.append({"rental_id": k, "station_id": r["station_id"], "start_date": r["start_date"],
                    "start_hour": int(r["start_hour"]), "duration_min": int(r["duration_min"]),
                    "rider_type": r["rider_type"], "rider_id": int(r["rider_id"])})
    return out


# ---------- 2. the plan ----------

def validate_plan(plan):
    """Raise ValueError unless step ids are unique, kinds are query, check or recommend, a query has sql,
    a check names its check, and every dependency is an earlier step. Return the list of step ids."""
    seen = []
    for step in plan:
        sid = step.get("step")
        if not sid or sid in seen:
            raise ValueError("step id %r is missing or repeated" % sid)
        if step.get("kind") not in STEP_KINDS:
            raise ValueError("step %s has unknown kind %r" % (sid, step.get("kind")))
        if step["kind"] == "query" and not step.get("sql", "").strip():
            raise ValueError("query step %s has no sql" % sid)
        if step["kind"] == "check" and step.get("check") not in ("reconcile", "noise"):
            raise ValueError("check step %s names no known check" % sid)
        for dep in step.get("depends_on", []):
            if dep not in seen:
                raise ValueError("step %s depends on %s, which is not an earlier step" % (sid, dep))
        seen.append(sid)
    return seen


# ---------- 3. the checks (code, not a model) ----------

def reconcile(total_rows, zone_rows, months=("2026-08", "2026-09")):
    """Do the zones add up to the totals? {"passed": bool, "diffs": {month: zone sum - total}}."""
    totals = {r["month"]: r["rentals"] for r in total_rows}
    diffs = {}
    for m in months:
        zone_sum = sum(r["rentals"] for r in zone_rows if r["month"] == m)
        diffs[m] = zone_sum - totals.get(m, 0)
    return {"passed": all(d == 0 for d in diffs.values()), "diffs": diffs}


def permutation_p(a, b):
    """Exact two-sided permutation p-value for the difference in means of a and b: the share of all
    ways to split the pooled values into groups of len(a) and len(b) whose difference is at least
    as large as the observed one. 1.0 if either list is empty."""
    if not a or not b:
        return 1.0
    pooled, n_a, total = list(a) + list(b), len(a), sum(a) + sum(b)
    observed = abs(sum(a) / len(a) - sum(b) / len(b))
    hits = count = 0
    for idx in itertools.combinations(range(len(pooled)), n_a):
        s = sum(pooled[i] for i in idx)
        diff = abs(s / n_a - (total - s) / (len(pooled) - n_a))
        hits += diff >= observed - 1e-9
        count += 1
    return hits / count


def noise_check(daily_rows):
    """Daily counts (rows with start_date, month, rentals) split into August and September.
    {"passed": both months have days, "n_aug", "n_sep", "mean_aug", "mean_sep", "p_value"}."""
    aug = [r["rentals"] for r in daily_rows if r["month"] == "2026-08"]
    sep = [r["rentals"] for r in daily_rows if r["month"] == "2026-09"]
    return {"passed": bool(aug) and bool(sep), "n_aug": len(aug), "n_sep": len(sep),
            "mean_aug": sum(aug) / len(aug) if aug else 0.0, "mean_sep": sum(sep) / len(sep) if sep else 0.0,
            "p_value": permutation_p(aug, sep)}


# ---------- 4. every number in the draft ----------

def parse_number(text):
    """'1,234' -> (1234.0, 0); '49.7%' -> (49.7, 1); '+2.2%' -> (2.2, 1). The second value is the decimals stated."""
    t = text.strip().rstrip("%").replace(",", "")
    decimals = len(t.split(".")[1]) if "." in t else 0
    return float(t), decimals


def _lookup(ref, results, status):
    """(value, None) for a cited cell, or (None, verdict) when it cannot be read."""
    step = ref["step"]
    if status.get(step) != "done":
        return None, "not_run"
    rows = [r for r in results.get(step) or [] if all(str(r.get(k)) == str(v) for k, v in ref.get("where", {}).items())]
    if len(rows) != 1:
        return None, "no_such_row"
    parts = [p.strip() for p in ref["expr"].split("/")]
    try:
        values = [float(rows[0][p]) for p in parts]
    except (KeyError, TypeError, ValueError):
        return None, "no_such_row"
    if len(values) == 2:
        return (values[0] / values[1], None) if values[1] else (None, "no_such_row")
    return values[0], None


def check_claims(draft, results, status):
    """{"verdicts": {claim id: ok | mismatch | not_run | no_such_row | assumption}, "uncited": [number texts]}.

    A claim matches when it equals the cited value at the precision it states: within 0.5 x 10^-d
    for d decimals. kinds: value (one cell, expr 'col' or 'col / col'), count (rows matching where),
    pct_change ((to - from) / from x 100), pct_fall ((from - to) / from x 100), assumption.
    A step whose status is not 'done' cannot back a claim (not_run). Every number in the text that is
    not the text of some claim is uncited.
    """
    verdicts = {}
    for c in draft["claims"]:
        kind = c["kind"]
        if kind == "assumption":
            verdicts[c["id"]] = "assumption"
            continue
        if kind == "count":
            if status.get(c["step"]) != "done":
                verdicts[c["id"]] = "not_run"
                continue
            actual = float(sum(1 for r in results.get(c["step"]) or []
                               if all(str(r.get(k)) == str(v) for k, v in c.get("where", {}).items())))
        elif kind in ("pct_change", "pct_fall"):
            start, bad = _lookup(c["from"], results, status)
            end, bad2 = _lookup(c["to"], results, status)
            if bad or bad2:
                verdicts[c["id"]] = bad or bad2
                continue
            if not start:
                verdicts[c["id"]] = "no_such_row"
                continue
            actual = (end - start) / start * 100 if kind == "pct_change" else (start - end) / start * 100
        else:
            actual, bad = _lookup(c, results, status)
            if bad:
                verdicts[c["id"]] = bad
                continue
        claimed, decimals = parse_number(c["text"])
        verdicts[c["id"]] = "ok" if abs(actual - claimed) <= 0.5 * 10 ** (-decimals) + 1e-9 else "mismatch"
    cited = {c["text"] for c in draft["claims"]}
    uncited = [t for t in NUMBER.findall(draft["text"]) if t not in cited]
    return {"verdicts": verdicts, "uncited": uncited}


def release(plan, status, results, report):
    """{"released": bool, "reasons": [...]}: release only if every check step ran and passed, every
    claim is ok or a labelled assumption, and no number is uncited."""
    reasons = []
    for step in plan:
        if step["kind"] != "check":
            continue
        sid = step["step"]
        if status.get(sid) != "done":
            reasons.append("check %s did not run" % sid)
        elif not results[sid][0]["passed"]:
            reasons.append("check %s failed" % sid)
    for cid, verdict in sorted(report["verdicts"].items(), key=lambda kv: int(kv[0][1:]) if kv[0][1:].isdigit() else 0):
        if verdict not in ("ok", "assumption"):
            reasons.append("claim %s: %s" % (cid, verdict))
    for t in report["uncited"]:
        reasons.append("uncited number %s" % t)
    return {"released": not reasons, "reasons": reasons}


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
    validate_plan(plan)
    decisions = {}
    for a in approvals:
        decisions[a["step"]] = a
    status, results, log = {}, {}, []
    executed = 0
    stopped = False
    for step in plan:
        sid = step["step"]
        entry = {"step": sid, "status": "", "detail": "", "sql_sha256": ""}
        log.append(entry)
        if stopped:
            entry["status"] = "not_reached"
            status[sid] = entry["status"]
            continue
        a = decisions.get(sid)
        sql = step.get("sql", "")
        if a is None or a["decision"] not in ("approve", "edit", "reject") or (a["decision"] == "edit" and not a["edited_sql"].strip()):
            entry["status"], entry["detail"] = "halted", "waiting for a valid approval"
            stopped = True
        elif a["decision"] == "reject":
            entry["status"], entry["detail"] = "rejected", a.get("note", "")
        elif any(status.get(d) != "done" for d in step.get("depends_on", [])):
            entry["status"] = "skipped"
            entry["detail"] = "needs " + ", ".join(d for d in step["depends_on"] if status.get(d) != "done")
        elif executed >= max_steps:
            entry["status"], entry["detail"] = "halted", "step budget of %d used" % max_steps
            stopped = True
        else:
            executed += 1
            if a["decision"] == "edit":
                sql = a["edited_sql"]
                entry["detail"] = "ran the reviewer's edit"
            if step["kind"] == "query":
                out = run_guarded(path, sql)
                entry["sql_sha256"] = sql_hash(sql)
                if out["status"] in ("ok", "truncated"):
                    entry["status"] = "done"
                    results[sid] = [dict(zip(out["columns"], row)) for row in out["rows"]]
                else:
                    entry["status"] = "blocked" if out["status"] == "blocked" else "failed"
                    entry["detail"] = out["reason"]
            elif step["kind"] == "check":
                deps = step["depends_on"]
                if step["check"] == "reconcile":
                    out = reconcile(results[deps[0]], results[deps[1]])
                else:
                    out = noise_check(results[deps[0]])
                results[sid] = [out]
                entry["status"] = "done"
                entry["detail"] = "passed" if out["passed"] else "FAILED"
            else:
                report = check_claims(draft, results, status)
                verdict = release(plan, status, results, report)
                results[sid] = {"claims": report, "release": verdict}
                entry["status"] = "done"
                entry["detail"] = "released" if verdict["released"] else "not released"
        status[sid] = entry["status"]
    return {"status": status, "results": results, "log": log}


def per_day_parts(results):
    """Weekend rentals per weekend day for August and September, split into Riverside, other zones and
    rentals the zone join could not place: {month: {"Riverside": x, "Other zones": y, "Unplaced": z}}."""
    out = {}
    for m in ("2026-08", "2026-09"):
        total = [r for r in results["S1"] if r["month"] == m][0]
        riv = sum(r["rentals"] for r in results["S2"] if r["month"] == m and r["zone"] == "Riverside")
        other = sum(r["rentals"] for r in results["S2"] if r["month"] == m and r["zone"] != "Riverside")
        days = total["days"]
        out[m] = {"Riverside": riv / days, "Other zones": other / days, "Unplaced": (total["rentals"] - riv - other) / days}
    return out


def draw_chart(parts, path):
    """A stacked bar per month, weekend rentals per weekend day, in plain SVG."""
    colours = {"Riverside": "#4a78a8", "Other zones": "#9cb8d6", "Unplaced": "#d9a441"}
    width, height, left, base, scale = 520, 330, 70, 270, 8.0
    parts_svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" font-family="sans-serif" font-size="13">' % (width, height),
                 '<rect width="100%" height="100%" fill="white"/>',
                 '<text x="%d" y="22" font-size="14">Weekend rentals per weekend day (synthetic data)</text>' % left,
                 '<line x1="%d" x2="%d" y1="%d" y2="%d" stroke="#555"/>' % (left, left + 260, base, base)]
    for i, (month, label) in enumerate((("2026-08", "August"), ("2026-09", "September"))):
        x, y = left + 30 + i * 120, base
        for name in ("Riverside", "Other zones", "Unplaced"):
            h = parts[month][name] * scale
            parts_svg.append('<rect x="%d" y="%.1f" width="70" height="%.1f" fill="%s"/>' % (x, y - h, h, colours[name]))
            y -= h
        total = sum(parts[month].values())
        parts_svg.append('<text x="%d" y="%.1f">%.1f</text>' % (x + 20, y - 6, total))
        parts_svg.append('<text x="%d" y="%d">%s</text>' % (x + 8, base + 18, label))
    for t in (0, 10, 20, 30):
        parts_svg.append('<text x="%d" y="%.1f" fill="#555">%d</text>' % (left - 24, base - t * scale + 4, t))
    for j, name in enumerate(("Riverside", "Other zones", "Unplaced")):
        parts_svg.append('<rect x="360" y="%d" width="14" height="14" fill="%s"/>' % (80 + j * 22, colours[name]))
        parts_svg.append('<text x="380" y="%d">%s</text>' % (92 + j * 22, name))
    parts_svg.append("</svg>")
    with open(path, "w") as f:
        f.write("\n".join(parts_svg) + "\n")


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
    parts = per_day_parts(run["results"])
    for m, p in parts.items():
        print(m, "per weekend day", {k: round(v, 2) for k, v in p.items()}, "total %.2f" % sum(p.values()))
    draw_chart(parts, os.path.join(HERE, "solution", "weekend_per_day.svg"))


if __name__ == "__main__":
    main()
