"""Exercise: load the model's JSON into a table, and reject what does not match the contract.

Fill in the functions marked TODO. Then run: python3 test_lesson.py
"""
import csv
import json
import math
import os
import re
import sqlite3

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

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
    """Undo the wrapping a model adds around good JSON. Return (text or None, list of repairs made).

    Allowed repairs, none of which changes a value: remove a ``` code fence, cut any
    text before the JSON starts and after it ends, remove a comma right before } or ].
    Return (None, repairs) when there is no JSON object or list in the text at all.
    """
    # TODO
    raise NotImplementedError


def type_ok(value, wanted):
    """True if value has the JSON type wanted: 'string', 'boolean', 'integer' or 'number'.

    Be strict. Think about what isinstance(True, int) returns, and about NaN.
    """
    # TODO
    raise NotImplementedError


def validate(obj, schema=SCHEMA):
    """Return a list of problems (strings). An empty list means obj matches the schema.

    Check: it is an object, no key is missing, no key is unexpected, null only where
    nullable, then type, enum, min, max and pattern for each value.
    """
    # TODO
    raise NotImplementedError


def parse(raw, schema=SCHEMA):
    """Return (record, "") for a valid output, or (None, reason) for a rejected one."""
    # TODO: repair, then json.loads, then validate
    raise NotImplementedError


def process(rows, schema=SCHEMA):
    """Return (valid, rejects).

    valid: one dict per good output, holding message_id plus the five fields.
    rejects: one (message_id, reason) tuple per bad output.
    """
    # TODO
    raise NotImplementedError


def load_into_sqlite(conn, valid, rejects):
    """Create tables complaints and rejects, and insert the rows.

    complaints: message_id, order_id, issue, refund_requested (0 or 1), amount_rs, severity.
    rejects: message_id, reason. Add CHECK constraints as a second wall behind validate().
    """
    # TODO
    raise NotImplementedError


def issue_counts(conn):
    """Return [(issue, complaints)] from the complaints table, most first, ties by issue name."""
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    rows = load_outputs()
    valid, rejects = process(rows)
    conn = sqlite3.connect(":memory:")
    load_into_sqlite(conn, valid, rejects)
    print("loaded", len(valid), "rejected", len(rejects))
    print(issue_counts(conn))
