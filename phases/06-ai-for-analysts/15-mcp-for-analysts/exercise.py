"""Exercise: a read-only data server for an AI assistant, speaking JSON-RPC style messages
in the shape MCP uses (tools/list and tools/call), in the standard library.

The data, the database, the read-only guard, the tools and serve() are given. Fill in the
functions marked TODO. Then run: python3 test_lesson.py
"""
import csv
import json
import os
import pathlib
import sqlite3
import time

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MAX_ROWS = 50
SERVER_INFO = {"name": "tiffinbell-readonly", "version": "1.0"}
# The analyst's choice for this client. export_table exists on the server but is not on it.
ALLOWED_TOOLS = {"list_tables", "describe_table", "run_query", "get_metric"}
# JSON-RPC 2.0 error codes (reference only: see https://www.jsonrpc.org/specification).
PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, INVALID_PARAMS = -32700, -32600, -32601, -32602

# ---------- given: data, database, the read-only guard, the tools ----------

SCHEMA = {
    "customers": "CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, name TEXT, phone TEXT, city TEXT, signup_date TEXT)",
    "orders": "CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER, order_date TEXT, status TEXT, amount REAL)",
    "reviews": "CREATE TABLE reviews (review_id INTEGER PRIMARY KEY, order_id INTEGER, rating INTEGER, comment TEXT)",
    "payouts": "CREATE TABLE payouts (restaurant TEXT, month TEXT, amount REAL)",
}
READABLE = {"customers": ["customer_id", "name", "city", "signup_date"],
            "orders": ["order_id", "customer_id", "order_date", "status", "amount"],
            "reviews": ["review_id", "order_id", "rating", "comment"]}
READ_ACTIONS = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}


class ToolError(Exception):
    """The tool ran and refused or failed. Reported as a result with isError true."""


def load_csv(name, data_dir=DATA):
    with open(os.path.join(data_dir, name), newline="") as f:
        return list(csv.DictReader(f))


def build_db(path, tables):
    if os.path.exists(path):
        os.remove(path)
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


def _authorize(action, table, column, db_name, trigger):
    if action not in READ_ACTIONS:
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_READ:
        table = table.lower()  # SQLite passes the name as typed: COUNT(*) FROM PAYOUTS gives "PAYOUTS"
        # COUNT(*) reads no column, so it comes with no database name (db_name None), on a stored
        # table and on a WITH name alike. Only a name that is not a stored table is a WITH name.
        if db_name is None and table not in SCHEMA and not table.startswith(("sqlite_", "pragma_")):
            return sqlite3.SQLITE_OK
        if table not in READABLE or (column and column not in READABLE[table]):
            return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def guarded_query(db_path, sql, max_rows=MAX_ROWS, max_seconds=0.5):
    """The read-only gateway from lesson 06-10, short version. Returns (columns, rows, truncated)."""
    text = sql.strip().rstrip(";")
    if not text or ";" in text:
        raise ToolError("send exactly one statement")
    if text.split(None, 1)[0].upper() not in ("SELECT", "WITH"):
        raise ToolError("only SELECT or WITH is allowed")
    conn = sqlite3.connect(pathlib.Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON")
    conn.set_authorizer(_authorize)
    deadline = time.monotonic() + max_seconds
    conn.set_progress_handler(lambda: time.monotonic() > deadline, 1000)
    try:
        cur = conn.execute(text)
        rows = cur.fetchmany(max_rows + 1)
        columns = [d[0] for d in cur.description]
    except sqlite3.Error as e:
        raise ToolError("query refused or failed: %s" % e)
    finally:
        conn.close()
    return columns, [list(r) for r in rows[:max_rows]], len(rows) > max_rows


def make_catalogue(db_path, metrics, export_dir):
    """Every tool the server knows: {name: {"description", "inputSchema", "fn"}}.
    export_table writes a file and must never be offered to an assistant; it is here because
    real servers often ship tools you should not turn on."""
    by_metric = {m["metric"]: m for m in metrics}

    def list_tables(args):
        return ", ".join(sorted(READABLE))

    def describe_table(args):
        if args["table"] not in READABLE:
            raise ToolError("no readable table called %s" % args["table"])
        return "%s: %s" % (args["table"], ", ".join(READABLE[args["table"]]))

    def run_query(args):
        columns, rows, truncated = guarded_query(db_path, args["sql"])
        return json.dumps({"columns": columns, "rows": rows, "truncated": truncated})

    def get_metric(args):
        if args["metric"] not in by_metric:
            raise ToolError("no metric called %s; known: %s" % (args["metric"], ", ".join(sorted(by_metric))))
        m = by_metric[args["metric"]]
        return "%s: %s SQL: %s" % (m["metric"], m["definition"], m["sql"])

    def export_table(args):
        with open(os.path.join(export_dir, args["table"] + ".csv"), "w") as f:
            f.write("exported\n")
        return "exported %s" % args["table"]

    def schema(**props):
        return {"type": "object", "properties": {k: {"type": v} for k, v in props.items()},
                "required": sorted(props), "additionalProperties": False}

    return {
        "list_tables": {"description": "Names of the tables you may read.", "inputSchema": schema(), "fn": list_tables},
        "describe_table": {"description": "Columns of one table you may read.", "inputSchema": schema(table="string"), "fn": describe_table},
        "run_query": {"description": "Run one read-only SELECT. At most %d rows come back." % MAX_ROWS,
                      "inputSchema": schema(sql="string"), "fn": run_query},
        "get_metric": {"description": "The agreed definition and SQL of a metric.", "inputSchema": schema(metric="string"), "fn": get_metric},
        "export_table": {"description": "Write a whole table to a CSV file.", "inputSchema": schema(table="string"), "fn": export_table},
    }


def make_state(db_path, metrics, export_dir, allowed=ALLOWED_TOOLS):
    """Everything the server needs: the tool catalogue, this client's allowlist, and the audit log."""
    return {"catalogue": make_catalogue(db_path, metrics, export_dir), "allowed": set(allowed), "log": []}


def serve(state, in_stream, out_stream):
    """Read one JSON request per line, write one JSON response per line (none for a notification)."""
    for line in in_stream:
        if line.strip():
            response = handle(state, line.strip())
            if response is not None:
                out_stream.write(response + "\n")
                out_stream.flush()


# ---------- the server ----------

def validate_args(schema, args):
    """Problems with args against a schema of the shape make_catalogue uses. [] if none.

    Checks, in this order: args is an object; every required property is present; no
    property outside "properties" when additionalProperties is false; each present property
    has its type ("string" or "integer"; True and False are not integers).
    """
    # TODO
    raise NotImplementedError


def _error(id_, code, message):
    return json.dumps({"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}})


def _result(id_, result):
    return json.dumps({"jsonrpc": "2.0", "id": id_, "result": result})


def handle(state, line):
    """Handle one request line. Return the response as a JSON string, or None for a notification.

    1. Not valid JSON: error -32700, id null.
    2. Not an object, jsonrpc not "2.0", method not a string, id present but not a string or
       integer, or params present but not an object: error -32600 (with the id when it is valid).
    3. No "id": a notification. Do it if it is known, reply nothing.
    4. initialize: result {"serverInfo": SERVER_INFO, "capabilities": {"tools": {}}}.
       tools/list: result {"tools": [{"name", "description", "inputSchema"}]}, allowed tools
       only, sorted by name.
       tools/call: params {"name", "arguments" (default {})}. A tool that is not in the
       catalogue or not allowed: -32602 "unknown tool" (the same message for both). Arguments
       that fail validate_args: -32602 with the problems. Otherwise run it: result
       {"content": [{"type": "text", "text": output}], "isError": false}, or, if it raises,
       the same with the error message as text and "isError": true.
       Anything else: -32601.
    Append one entry to state["log"] for every line: {"seq" (1, 2, ...), "id", "method", "tool",
    "outcome" (result, tool_error, error or notification), "code" (the error code or None)}.
    """
    # TODO
    raise NotImplementedError


def summarise_log(log, allowed=ALLOWED_TOOLS):
    """{"requests", "result", "tool_error", "error", "notification", "refused_tools"}:
    counts of each outcome, and the sorted names of tools that were called but are not in
    allowed (these are the requests to read first)."""
    # TODO
    raise NotImplementedError


def main():
    import io
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "tiffinbell.db")
        build_db(path, {name: load_csv(name + ".csv") for name in SCHEMA})
        export_dir = os.path.join(tmp, "exports")
        os.makedirs(export_dir)
        state = make_state(path, load_csv("metrics.csv"), export_dir)
        session = load_csv("session.csv")
        out = io.StringIO()
        serve(state, io.StringIO("".join(s["request"] + "\n" for s in session)), out)
        replies = iter(out.getvalue().splitlines())
        for s, entry in zip(session, state["log"]):
            if entry["outcome"] == "notification":
                shown = "(no reply)"
            else:
                reply = json.loads(next(replies))
                if "error" in reply:
                    shown = "error %d %s" % (reply["error"]["code"], reply["error"]["message"])
                elif "content" in reply["result"]:
                    shown = ("isError " if reply["result"]["isError"] else "") + reply["result"]["content"][0]["text"][:60]
                else:
                    shown = ", ".join(sorted(reply["result"]))
            print("%2s %-12s %-16s %s" % (s["seq"], entry["outcome"], entry["tool"] or entry["method"] or "-", shown))
        print(summarise_log(state["log"], state["allowed"]))
        print("files exported:", os.listdir(export_dir))


if __name__ == "__main__":
    main()
