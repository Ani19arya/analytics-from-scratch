"""Solution: turn model JSON into table rows you can trust, or reject it with a reason."""
import csv
import json
import math
import os
import re
import sqlite3

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# The contract the prompt asked for. Every key is required. amount_rs may be null.
SCHEMA = {
    "order_id": {"type": "string", "pattern": r"^TB-[0-9]{5}$"},
    "issue": {"type": "string", "enum": ["late", "missing_item", "wrong_item", "cold_food", "other"]},
    "refund_requested": {"type": "boolean"},
    "amount_rs": {"type": "number", "nullable": True, "min": 0, "max": 5000},
    "severity": {"type": "integer", "min": 1, "max": 5},
}


def load_outputs(path=os.path.join(DATA, "outputs.csv")):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def repair(raw):
    """Undo the wrapping a model adds around good JSON. Return (text or None, list of repairs).

    Only three repairs are made, and none of them changes a value:
    a ``` code fence is removed, text before the first { or [ and after the last } or ] is cut,
    and a comma right before a closing } or ] is removed.
    """
    text = raw.strip()
    repairs = []
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.S)
    if fence:
        text = fence.group(1)
        repairs.append("removed code fence")
    if not text.startswith(("{", "[")):
        starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
        start = min(starts) if starts else -1
        end = max(text.rfind("}"), text.rfind("]"))
        if start == -1 or end < start:
            return None, repairs
        text = text[start:end + 1]
        repairs.append("cut text around the JSON")
    fixed = re.sub(r",\s*([}\]])", r"\1", text)
    if fixed != text:
        repairs.append("removed trailing comma")
    return fixed, repairs


def type_ok(value, wanted):
    """JSON types, checked strictly. In Python True is an int, so booleans are ruled out by hand."""
    if wanted == "string":
        return isinstance(value, str)
    if wanted == "boolean":
        return isinstance(value, bool)
    if wanted == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if wanted == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    raise ValueError("unknown type " + wanted)


def validate(obj, schema=SCHEMA):
    """Return a list of problems. An empty list means the object matches the schema."""
    if not isinstance(obj, dict):
        return ["not a JSON object"]
    problems = []
    for key in schema:
        if key not in obj:
            problems.append("missing key %s" % key)
    for key in sorted(obj):
        if key not in schema:
            problems.append("unexpected key %s" % key)
    for key, rule in schema.items():
        if key not in obj:
            continue
        value = obj[key]
        if value is None:
            if not rule.get("nullable"):
                problems.append("%s is null" % key)
            continue
        if not type_ok(value, rule["type"]):
            problems.append("%s should be %s, got %r" % (key, rule["type"], value))
            continue
        if "enum" in rule and value not in rule["enum"]:
            problems.append("%s %r is not one of the allowed values" % (key, value))
        if "min" in rule and value < rule["min"]:
            problems.append("%s %r is below %r" % (key, value, rule["min"]))
        if "max" in rule and value > rule["max"]:
            problems.append("%s %r is above %r" % (key, value, rule["max"]))
        if "pattern" in rule and not re.match(rule["pattern"], value):
            problems.append("%s %r has the wrong format" % (key, value))
    return problems


def parse(raw, schema=SCHEMA):
    """Return (record or None, reason). The reason is '' for a valid record."""
    text, _ = repair(raw)
    if text is None:
        return None, "no JSON object found"
    try:
        obj = json.loads(text)
    except ValueError as e:
        return None, "unparseable: %s" % e
    problems = validate(obj, schema)
    if problems:
        return None, problems[0]
    return obj, ""


def process(rows, schema=SCHEMA):
    """Split rows into (valid, rejects). valid: dicts with message_id and the fields.
    rejects: (message_id, reason) tuples."""
    valid, rejects = [], []
    for row in rows:
        record, reason = parse(row["raw_output"], schema)
        if record is None:
            rejects.append((row["message_id"], reason))
        else:
            out = {"message_id": row["message_id"]}
            out.update(record)
            valid.append(out)
    return valid, rejects


def load_into_sqlite(conn, valid, rejects):
    """Create the two tables and insert. The CHECK constraints are a second wall behind validate()."""
    conn.execute("""CREATE TABLE complaints (
        message_id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL,
        issue TEXT NOT NULL CHECK (issue IN ('late', 'missing_item', 'wrong_item', 'cold_food', 'other')),
        refund_requested INTEGER NOT NULL CHECK (refund_requested IN (0, 1)),
        amount_rs REAL CHECK (amount_rs IS NULL OR amount_rs BETWEEN 0 AND 5000),
        severity INTEGER NOT NULL CHECK (typeof(severity) = 'integer' AND severity BETWEEN 1 AND 5))""")
    conn.execute("CREATE TABLE rejects (message_id TEXT PRIMARY KEY, reason TEXT NOT NULL)")
    conn.executemany(
        "INSERT INTO complaints VALUES (:message_id, :order_id, :issue, :refund_requested, :amount_rs, :severity)",
        [dict(r, refund_requested=int(r["refund_requested"])) for r in valid])
    conn.executemany("INSERT INTO rejects VALUES (?, ?)", rejects)
    conn.commit()


def issue_counts(conn):
    """[(issue, complaints)], most first, ties by issue name."""
    return conn.execute("SELECT issue, COUNT(*) FROM complaints GROUP BY issue ORDER BY COUNT(*) DESC, issue").fetchall()


def main():
    rows = load_outputs()
    valid, rejects = process(rows)
    conn = sqlite3.connect(":memory:")
    load_into_sqlite(conn, valid, rejects)
    print("outputs %d, loaded %d, rejected %d" % (len(rows), len(valid), len(rejects)))
    for issue, n in issue_counts(conn):
        print("  %-13s %d" % (issue, n))
    kinds = {}
    for _, reason in rejects:
        kind = reason.split()[0].rstrip(":")
        kinds[kind] = kinds.get(kind, 0) + 1
    print("rejects by first word of the reason:", dict(sorted(kinds.items())))

if __name__ == "__main__":
    main()
