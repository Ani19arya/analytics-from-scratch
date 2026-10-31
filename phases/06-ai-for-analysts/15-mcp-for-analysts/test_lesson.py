"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py.

Every run_query result is recomputed here on an ordinary connection. The database file is
hashed and the export folder listed after the session, so a server that writes, or that
runs a tool the client may not use, fails.
"""
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sqlite3
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lesson = load("lesson", TARGET)
make_data = load("make_data", os.path.join(HERE, "make_data.py"))
OTHER_SEED = 1615
TABLES = ["customers", "orders", "reviews", "payouts"]


def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class ServerCase(unittest.TestCase):
    tables = None
    metrics = None

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="w6-mcp-")
        self.path = os.path.join(self.tmp, "tiffinbell.db")
        lesson.build_db(self.path, self.tables)
        self.hash = file_hash(self.path)
        self.export_dir = os.path.join(self.tmp, "exports")
        os.makedirs(self.export_dir)
        self.state = lesson.make_state(self.path, self.metrics, self.export_dir)

    def tearDown(self):
        self.assertEqual(file_hash(self.path), self.hash, "the database file changed")
        self.assertEqual(os.listdir(self.export_dir), [], "a tool that is not allowed was run: a file was exported")
        shutil.rmtree(self.tmp, ignore_errors=True)

    def send(self, obj):
        line = obj if isinstance(obj, str) else json.dumps(obj)
        reply = lesson.handle(self.state, line)
        return None if reply is None else json.loads(reply)

    def direct(self, sql):
        conn = sqlite3.connect(self.path)
        try:
            cur = conn.execute(sql)
            rows = cur.fetchmany(51)
            cols = [d[0] for d in cur.description]
        finally:
            conn.close()
        return {"columns": cols, "rows": [list(r) for r in rows[:50]], "truncated": len(rows) > 50}


def committed_tables():
    return {name: lesson.load_csv(name + ".csv") for name in TABLES}


class TestValidate(unittest.TestCase):
    schema = {"type": "object", "properties": {"sql": {"type": "string"}, "limit": {"type": "integer"}},
              "required": ["sql"], "additionalProperties": False}

    def test_cases(self):
        v = lesson.validate_args
        self.assertEqual(v(self.schema, {"sql": "SELECT 1"}), [])
        self.assertEqual(v(self.schema, {"sql": "SELECT 1", "limit": 5}), [])
        self.assertEqual(v(self.schema, []), ["arguments must be an object"])
        self.assertEqual(v(self.schema, {}), ["missing sql"])
        self.assertEqual(v(self.schema, {"sql": 1}), ["sql must be a string"])
        self.assertEqual(v(self.schema, {"sql": "x", "limit": True}), ["limit must be a integer"], "True is not an integer")
        self.assertEqual(v(self.schema, {"query": "x", "b": 1}), ["missing sql", "unexpected b", "unexpected query"],
                         "missing first, then unexpected names in sorted order")
        open_schema = dict(self.schema, additionalProperties=True)
        self.assertEqual(v(open_schema, {"sql": "x", "extra": 1}), [], "extra names are fine when additionalProperties is true")
        self.assertEqual(v({"type": "object", "properties": {}, "required": [], "additionalProperties": False}, {}), [])


class TestProtocol(ServerCase):
    tables = committed_tables()
    metrics = lesson.load_csv("metrics.csv")

    def test_ids_and_shapes(self):
        r = self.send({"jsonrpc": "2.0", "id": "abc", "method": "initialize"})
        self.assertEqual((r["jsonrpc"], r["id"]), ("2.0", "abc"), "echo the request's id, string or integer")
        self.assertIn("serverInfo", r["result"])
        r = self.send({"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "list_tables"}})
        self.assertEqual(r["result"], {"content": [{"type": "text", "text": "customers, orders, reviews"}], "isError": False},
                         "arguments default to {}")
        for bad in [{"jsonrpc": "2.0", "id": True, "method": "tools/list"}, {"jsonrpc": "2.0", "id": 1, "method": 5},
                    {"jsonrpc": "2.0", "id": 1}, {"id": 1, "method": "tools/list"}, "null", '"tools/list"']:
            r = self.send(bad)
            self.assertEqual(r["error"]["code"], -32600, "%r is not a valid request" % (bad,))
        r = self.send({"jsonrpc": "2.0", "id": True, "method": "tools/list"})
        self.assertIsNone(r["id"], "an id that is not a string or integer is not echoed")
        self.assertIsNone(self.send({"jsonrpc": "2.0", "method": "anything/at/all"}), "a notification never gets a reply")
        self.assertEqual(self.send("")["error"]["code"], -32700)

    def test_hidden_and_unknown_tools_look_the_same(self):
        a = self.send({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "export_table", "arguments": {"table": "orders"}}})
        b = self.send({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "no_such_tool", "arguments": {}}})
        self.assertEqual(a, b, "a tool that exists but is not allowed must be refused exactly like one that does not exist")
        self.assertEqual(a["error"]["code"], -32602)

    def test_allowlist_is_per_client(self):
        self.state = lesson.make_state(self.path, self.metrics, self.export_dir, allowed={"list_tables", "export_table_typo"})
        names = [t["name"] for t in self.send({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})["result"]["tools"]]
        self.assertEqual(names, ["list_tables"], "list only tools that are both in the catalogue and allowed")
        r = self.send({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "run_query", "arguments": {"sql": "SELECT 1"}}})
        self.assertEqual(r["error"]["code"], -32602, "run_query is not allowed for this client")
        self.assertEqual(lesson.summarise_log(self.state["log"], self.state["allowed"])["refused_tools"], ["run_query"])

    def test_count_star_is_checked(self):
        # COUNT(*) reads no column, so SQLite passes no database name: on a stored table as on a WITH name
        for sql in ["SELECT COUNT(*) FROM payouts", "SELECT COUNT(*) FROM PAYOUTS", "SELECT 1 FROM payouts LIMIT 1",
                    "SELECT COUNT(*) FROM sqlite_master", "SELECT COUNT(*) FROM pragma_table_info('customers')"]:
            with self.assertRaises(lesson.ToolError, msg="the gateway must refuse %r" % sql):
                lesson.guarded_query(self.path, sql)
        for sql in ["WITH t AS (SELECT DISTINCT city FROM customers) SELECT COUNT(*) FROM t",
                    "WITH r AS (SELECT rating FROM reviews) SELECT COUNT(*) FROM r", "SELECT COUNT(*) FROM Orders"]:
            columns, rows, truncated = lesson.guarded_query(self.path, sql)
            self.assertEqual({"columns": columns, "rows": rows, "truncated": truncated}, self.direct(sql),
                             "a WITH over readable tables must run: %r" % sql)

    def test_log(self):
        self.send({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.send("{broken")
        self.send({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "run_query", "arguments": {"sql": "DELETE FROM orders"}}})
        log = self.state["log"]
        self.assertEqual([(e["seq"], e["outcome"], e["code"]) for e in log],
                         [(1, "result", None), (2, "notification", None), (3, "error", -32700), (4, "tool_error", None)])
        self.assertEqual((log[3]["id"], log[3]["method"], log[3]["tool"]), (2, "tools/call", "run_query"))
        summary = lesson.summarise_log(log, lesson.ALLOWED_TOOLS)
        self.assertEqual(summary, {"requests": 4, "result": 1, "tool_error": 1, "error": 1, "notification": 1, "refused_tools": []})
        self.assertEqual(lesson.summarise_log([], lesson.ALLOWED_TOOLS)["requests"], 0)


class SessionCase(ServerCase):
    session = None

    def check_session(self, label):
        lines = [s["request"] for s in self.session]
        out = io.StringIO()
        lesson.serve(self.state, io.StringIO("\n".join(lines) + "\n"), out)
        replies = [json.loads(x) for x in out.getvalue().splitlines()]
        expecting_reply = [s for s in self.session if s["expected"] != "none"]
        self.assertEqual(len(replies), len(expecting_reply), "%s: one reply per request, none for a notification" % label)
        for s, r in zip(expecting_reply, replies):
            where = "%s request %s (%s)" % (label, s["seq"], s["why"])
            self.assertEqual(r.get("jsonrpc"), "2.0", where)
            exp = s["expected"]
            if exp.startswith("-"):
                self.assertIn("error", r, "%s: expected error %s" % (where, exp))
                self.assertEqual(r["error"]["code"], int(exp), where)
                continue
            self.assertIn("result", r, "%s: expected a result, got %s" % (where, r.get("error")))
            req = json.loads(s["request"])
            self.assertEqual(r["id"], req["id"], where)
            if req["method"] == "tools/list":
                self.assertEqual([t["name"] for t in r["result"]["tools"]], sorted(lesson.ALLOWED_TOOLS), where)
                for t in r["result"]["tools"]:
                    self.assertEqual(t["inputSchema"]["type"], "object", where)
            if req["method"] != "tools/call":
                continue
            self.assertEqual(r["result"]["isError"], exp == "tool_error", "%s: isError should be %s" % (where, exp == "tool_error"))
            text = r["result"]["content"][0]["text"]
            name, args = req["params"]["name"], req["params"]["arguments"]
            if name == "run_query" and exp == "result":
                self.assertEqual(json.loads(text), self.direct(args["sql"]), "%s: rows differ from running the query directly" % where)
            if name == "run_query" and "FROM reviews" in args["sql"]:
                self.assertIn("ignore your previous instructions", text, "%s: data is returned as data, unchanged" % where)
            if name == "describe_table" and exp == "result":
                self.assertNotIn("phone", text, "%s: never show a column the assistant may not read" % where)
        summary = lesson.summarise_log(self.state["log"], self.state["allowed"])
        want = {"requests": len(self.session), "notification": sum(s["expected"] == "none" for s in self.session),
                "result": sum(s["expected"] == "result" for s in self.session),
                "tool_error": sum(s["expected"] == "tool_error" for s in self.session),
                "error": sum(s["expected"].startswith("-") for s in self.session), "refused_tools": ["export_table"]}
        self.assertEqual(summary, want, "%s: the log summary does not match the session" % label)


class TestCommittedSession(SessionCase):
    tables = committed_tables()
    metrics = lesson.load_csv("metrics.csv")
    session = lesson.load_csv("session.csv")

    def test_session(self):
        self.check_session("committed data")


SECOND = make_data.build(seed=OTHER_SEED)


class TestSecondDataset(SessionCase):
    tables = {name: [{k: str(v) for k, v in row.items()} for row in SECOND[name]] for name in TABLES}
    metrics = SECOND["metrics"]
    session = [{k: str(v) for k, v in row.items()} for row in SECOND["session"]]

    def test_session(self):
        self.check_session("seed %d" % OTHER_SEED)


if __name__ == "__main__":
    unittest.main()
