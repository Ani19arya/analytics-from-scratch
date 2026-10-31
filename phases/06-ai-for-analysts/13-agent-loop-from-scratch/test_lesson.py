"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py.

Every run_sql observation is recomputed here on an ordinary connection, token costs are
recomputed with a running total instead of re-summing, and the database file is hashed
after every run, so a loop that lets a write through fails.
"""
import hashlib
import importlib.util
import json
import math
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
OTHER_SEED = 1613


def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def ref_tokens(text):
    return int(math.ceil(len(text) / 4.0))


def ref_cost(messages):
    """Running total: the context grows by each message; every assistant message pays for the context before it."""
    context = inp = out = calls = 0
    for m in messages:
        if m["role"] == "assistant":
            calls += 1
            inp += context
            out += ref_tokens(m["content"])
        context += ref_tokens(m["content"])
    return calls, inp, out, inp * 2.0 / 1000 + out * 8.0 / 1000


def turns_by_question(rows):
    out = {}
    for r in rows:
        out.setdefault(r["question_id"], []).append((int(r["turn"]), r["text"]))
    return {q: [t for _, t in sorted(v)] for q, v in out.items()}


class Echo:
    def __init__(self, replies):
        self.replies = list(replies)
        self.seen = []

    def __call__(self, messages):
        self.seen.append(len(messages))
        return self.replies.pop(0) if self.replies else ""


def tool_call(name, **args):
    return json.dumps({"tool": name, "args": args})


class TestPieces(unittest.TestCase):
    def test_parse_action(self):
        self.assertEqual(lesson.parse_action('{"final": "done"}'), ("final", "done"))
        self.assertEqual(lesson.parse_action('{"tool": "list_tables"}'), ("tool", "list_tables", {}),
                         "args is optional and defaults to {}")
        self.assertEqual(lesson.parse_action('{"tool": "run_sql", "args": {"sql": "SELECT 1"}}'), ("tool", "run_sql", {"sql": "SELECT 1"}))
        for bad in ["", "not json", '{"tool": "x"', "[1, 2]", '"final"', '{"final": "a", "tool": "b"}', "{}",
                    '{"final": 3}', '{"tool": "run_sql", "args": "SELECT 1"}', '{"tool": 5}']:
            got = lesson.parse_action(bad)
            self.assertEqual(got[0], "error", "%r is not a valid reply, so parse_action must return ('error', message)" % bad)
            self.assertTrue(got[1], "say what was wrong with %r" % bad)

    def test_call_tool(self):
        def boom(args):
            raise KeyError("missing")
        tools = {"echo": lambda args: "you said %s" % args.get("x"), "boom": boom}
        self.assertEqual(lesson.call_tool(tools, "echo", {"x": 1}), "you said 1")
        self.assertTrue(lesson.call_tool(tools, "nope", {}).startswith("error: "), "an unknown tool is an observation starting 'error: '")
        self.assertTrue(lesson.call_tool(tools, "boom", {}).startswith("error: "), "a tool that raises must not crash the loop")

    def test_ungrounded_numbers(self):
        f = lesson.ungrounded_numbers
        self.assertEqual(f("No numbers here.", ["rows: [(5,)]"]), [])
        self.assertEqual(f("Revenue was 1,234.50.", ["rows: [(1234.5,)]"]), [], "1,234.50 is 1234.5 written with 2 decimals")
        self.assertEqual(f("Share 12.3%", ["12.3456"]), [], "12.3456 rounds to 12.3 at one decimal")
        self.assertEqual(f("Share 12.4%", ["12.3456"]), ["12.4"])
        self.assertEqual(f("About 12%", ["11.6"]), [], "written as a whole number, 11.6 supports 12")
        self.assertEqual(f("In Q2 2026 it was 7", ["What about Q2 2026?", "rows: [(7,)]"]), [])
        self.assertEqual(f("7 and 8", []), ["7", "8"], "with no sources every number is unsupported")


class AgentCase(unittest.TestCase):
    tables = None
    questions = None
    turns = None

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="w6-agent-")
        cls.path = os.path.join(cls.tmp, "shop.db")
        lesson.build_db(cls.path, cls.tables)
        cls.hash = file_hash(cls.path)
        cls.tools = lesson.make_tools(cls.path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def direct(self, sql):
        conn = sqlite3.connect(self.path)
        try:
            rows = conn.execute(sql.strip().rstrip(";")).fetchmany(21)
        finally:
            conn.close()
        return "rows: %r (more rows not shown)" % rows[:20] if len(rows) > 20 else "rows: %r" % rows

    def expected_calls(self, q, max_steps, max_repeats=3):
        turns = self.turns[q["question_id"]]
        if q["expected_status"] in ("answered", "ungrounded"):
            return len(turns)
        if q["expected_status"] == "stuck":
            return max_repeats
        return max_steps

    def check_all(self, label):
        for q in self.questions:
            run = lesson.run_agent(q["question"], lesson.ScriptedModel(self.turns[q["question_id"]]), self.tools, 8, 3)
            self.assertEqual(file_hash(self.path), self.hash, "%s %s: the database changed" % (label, q["question_id"]))
            self.assertEqual(run["status"], q["expected_status"], "%s %s (%s): expected %s, got %s" % (
                label, q["question_id"], q["why"], q["expected_status"], run["status"]))
            want_calls = self.expected_calls(q, 8)
            self.assertEqual(len(run["steps"]), want_calls, "%s %s: expected %d model calls" % (label, q["question_id"], want_calls))
            msgs = run["messages"]
            self.assertEqual([m["role"] for m in msgs[:2]], ["system", "user"])
            self.assertEqual(msgs[1]["content"], q["question"])
            self.assertEqual(sum(m["role"] == "assistant" for m in msgs), want_calls, "one assistant message per model call")
            for step in run["steps"]:
                if step["kind"] == "tool" and step["tool"] == "run_sql":
                    obs = step["observation"]
                    sql = step["args"]["sql"]
                    should_block = "email" in sql or sql.split()[0].upper() not in ("SELECT", "WITH")
                    if should_block:
                        self.assertTrue(obs.startswith("error: "), "%s %s: %r must be blocked" % (label, q["question_id"], sql[:50]))
                    else:
                        self.assertEqual(obs, self.direct(sql), "%s %s: observation differs from running the SQL directly" % (label, q["question_id"]))
            if run["status"] == "answered":
                self.assertEqual(run["answer"], json.loads(self.turns[q["question_id"]][-1])["final"])
            calls, inp, out, credits = ref_cost(msgs)
            cost = lesson.run_cost(msgs)
            self.assertEqual((cost["calls"], cost["input_tokens"], cost["output_tokens"]), (calls, inp, out),
                             "%s %s: every call pays input tokens for all messages before it" % (label, q["question_id"]))
            self.assertAlmostEqual(cost["credits"], credits, places=9)

    def check_budgets(self):
        budgets = list(range(0, 9))
        table = lesson.budget_table(self.questions, self.turns, self.tools, budgets)
        self.assertEqual([r["max_steps"] for r in table], budgets)
        needed = [len(self.turns[q["question_id"]]) for q in self.questions if q["expected_status"] == "answered"]
        for row in table:
            want = sum(n <= row["max_steps"] for n in needed)
            self.assertEqual(row["answered"], want, "with max_steps %d, %d questions can finish" % (row["max_steps"], want))
        self.assertEqual(table[0]["credits"], 0.0, "max_steps 0 calls the model zero times")
        for a, b in zip(table, table[1:]):
            self.assertGreater(b["credits"], a["credits"], "a bigger budget never costs less here: the wandering script uses it all")
        self.assertEqual(lesson.recommend_budget(table), max(needed))


class TestLoopRules(AgentCase):
    tables = {"customers": [{"customer_id": 1, "name": "A", "email": "a@example.com", "country": "UK", "signup_date": "2025-01-01"}],
              "orders": [{"order_id": 1, "customer_id": 1, "order_date": "2026-01-02", "status": "completed", "amount": 10.5}]}

    def test_zero_steps(self):
        run = lesson.run_agent("Anything?", Echo(['{"final": "x"}']), self.tools, max_steps=0)
        self.assertEqual((run["status"], run["steps"]), ("step_limit", []), "max_steps 0 means the model is never called")

    def test_messages_grow(self):
        model = Echo([tool_call("list_tables"), '{"final": "There are 2 tables."}'])
        run = lesson.run_agent("How many tables?", model, self.tools)
        self.assertEqual(model.seen, [2, 4], "the model sees system + question, then also its reply and the tool result")
        self.assertEqual(run["status"], "ungrounded", "2 is not in the question or in 'customers, orders'")
        self.assertEqual([m["role"] for m in run["messages"]], ["system", "user", "assistant", "tool", "assistant"])

    def test_errors_are_observations(self):
        model = Echo(["oops", tool_call("python", code="1"), tool_call("run_sql", sql="SELECT email FROM customers"),
                      tool_call("run_sql", sql="SELECT COUNT(*) FROM orders"), '{"final": "1 order."}'])
        run = lesson.run_agent("How many orders?", model, self.tools)
        self.assertEqual(run["status"], "answered")
        obs = [s["observation"] for s in run["steps"][:3]]
        self.assertTrue(all(o.startswith("error: ") for o in obs), "a bad reply, an unknown tool and a blocked query all become 'error: ...' observations")
        self.assertEqual(run["steps"][3]["observation"], "rows: [(1,)]")

    def test_count_star_is_checked(self):
        # COUNT(*) reads no column, so SQLite passes no database name: on a stored table as on a WITH name
        for sql in ["SELECT COUNT(*) FROM sqlite_master", "SELECT COUNT(*) FROM SQLITE_MASTER", "SELECT 1 FROM sqlite_master LIMIT 1",
                    "SELECT COUNT(*) FROM pragma_table_info('customers')"]:
            with self.assertRaises(lesson.ToolError, msg="run_sql must refuse %r" % sql):
                lesson.run_sql_readonly(self.path, sql)
        for sql in ["WITH t AS (SELECT DISTINCT country FROM customers) SELECT COUNT(*) FROM t",
                    "WITH t AS (SELECT amount FROM orders) SELECT COUNT(*) FROM t", "SELECT COUNT(*) FROM Orders"]:
            self.assertEqual(lesson.run_sql_readonly(self.path, sql), "rows: [(1,)]", "a WITH over allowed tables must run: %r" % sql)
        self.assertEqual(file_hash(self.path), self.hash)

    def test_stuck_needs_repeats_in_a_row(self):
        a, b = tool_call("list_tables"), tool_call("describe_table", table="orders")
        run = lesson.run_agent("q", Echo([a, a, b, a, a, '{"final": "ok"}']), self.tools)
        self.assertEqual(run["status"], "answered", "two in a row, then a different call, is not stuck")
        run = lesson.run_agent("q", Echo([a, a, "bad", a, a, '{"final": "ok"}']), self.tools)
        self.assertEqual(run["status"], "answered", "a broken reply in between breaks the streak")
        run = lesson.run_agent("q", Echo([b, a, a, a, '{"final": "ok"}']), self.tools)
        self.assertEqual((run["status"], len(run["steps"])), ("stuck", 4), "the third identical call in a row stops the run")
        self.assertEqual(run["steps"][-1]["kind"], "stuck")
        same_args = [tool_call("describe_table", table="orders"), json.dumps({"args": {"table": "orders"}, "tool": "describe_table"})]
        run = lesson.run_agent("q", Echo(same_args + same_args), self.tools)
        self.assertEqual(run["status"], "stuck", "the same tool with the same args is a repeat even if the JSON is written differently")

    def test_cost_edge(self):
        self.assertEqual(lesson.run_cost([{"role": "system", "content": "abc"}]),
                         {"calls": 0, "input_tokens": 0, "output_tokens": 0, "credits": 0.0})
        self.assertIsNone(lesson.recommend_budget([]))
        tie = [{"max_steps": 3, "answered": 2, "credits": 1.0}, {"max_steps": 5, "answered": 2, "credits": 2.0},
               {"max_steps": 2, "answered": 1, "credits": 0.5}]
        self.assertEqual(lesson.recommend_budget(tie), 3)


class TestCommitted(AgentCase):
    tables = {"customers": lesson.load_csv("customers.csv"), "orders": lesson.load_csv("orders.csv")}
    questions = lesson.load_csv("questions.csv")
    turns = turns_by_question(lesson.load_csv("agent_script.csv"))

    def test_every_question(self):
        self.check_all("committed data")

    def test_budgets(self):
        self.check_budgets()


SECOND = make_data.build(seed=OTHER_SEED)


class TestSecondDataset(AgentCase):
    tables = {"customers": SECOND["customers"], "orders": SECOND["orders"]}
    questions = SECOND["questions"]
    turns = turns_by_question([{k: str(v) for k, v in r.items()} for r in SECOND["agent_script"]])

    def test_every_question(self):
        self.check_all("seed %d" % OTHER_SEED)

    def test_budgets(self):
        self.check_budgets()


if __name__ == "__main__":
    unittest.main()
