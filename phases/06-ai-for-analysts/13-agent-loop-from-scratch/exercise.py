"""Exercise: an analytics agent loop, built from scratch, run on a simulated model.

The tools, the database, the scripted model and numbers_in are given. Fill in the functions
marked TODO. Then run: python3 test_lesson.py
"""
import ast
import csv
import json
import operator
import os
import pathlib
import re
import sqlite3
import time

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SYSTEM = ("You are an analytics agent for the Larkspur Goods shop database. Tools: list_tables, describe_table(table), "
          "run_sql(sql), calculate(expression). Reply with one JSON object: {\"tool\": name, \"args\": {...}} "
          "to use a tool, or {\"final\": answer} to answer. Every number in your answer must come from a tool.")
# A fictional example rate card in made-up credits, not any provider's prices.
INPUT_CREDITS_PER_1K = 2.0
OUTPUT_CREDITS_PER_1K = 8.0

# ---------- given: data, database, tools ----------

SCHEMA = {
    "customers": "CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, name TEXT, email TEXT, country TEXT, signup_date TEXT)",
    "orders": "CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER, order_date TEXT, status TEXT, amount REAL)",
}
VISIBLE_COLUMNS = {"customers": ["customer_id", "name", "country", "signup_date"],
                   "orders": ["order_id", "customer_id", "order_date", "status", "amount"]}
BLOCKED_COLUMNS = {("customers", "email")}
READ_ACTIONS = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}
MAX_ROWS = 20


class ToolError(Exception):
    """A tool refused or failed. The loop turns it into an observation the model can read."""


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


def _authorize(action, arg1, arg2, db_name, trigger):
    if action not in READ_ACTIONS:
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_READ and db_name is not None:
        if arg1 not in VISIBLE_COLUMNS or (arg1, arg2) in BLOCKED_COLUMNS:
            return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def run_sql_readonly(db_path, sql, max_rows=MAX_ROWS, max_seconds=0.5):
    """A short version of the gateway from lesson 06-10: one SELECT or WITH, an allowlist
    authorizer, a read-only connection, a row cap and a time limit."""
    text = sql.strip().rstrip(";")
    if not text or ";" in text:
        raise ToolError("blocked: send exactly one statement")
    if text.split(None, 1)[0].upper() not in ("SELECT", "WITH"):
        raise ToolError("blocked: only SELECT or WITH is allowed")
    conn = sqlite3.connect(pathlib.Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON")
    conn.set_authorizer(_authorize)
    deadline = time.monotonic() + max_seconds
    conn.set_progress_handler(lambda: time.monotonic() > deadline, 1000)
    try:
        rows = conn.execute(text).fetchmany(max_rows + 1)
    except sqlite3.Error as e:
        raise ToolError("blocked or failed: %s" % e)
    finally:
        conn.close()
    if len(rows) > max_rows:
        return "rows: %r (more rows not shown)" % rows[:max_rows]
    return "rows: %r" % rows


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval(node.operand)
    raise ToolError("calculate only takes numbers, + - * / and brackets")


def make_tools(db_path):
    """The four tools, each a function of one dict of arguments that returns text."""
    def list_tables(args):
        return ", ".join(sorted(VISIBLE_COLUMNS))

    def describe_table(args):
        table = args.get("table")
        if table not in VISIBLE_COLUMNS:
            raise ToolError("no table called %r" % table)
        return "%s: %s" % (table, ", ".join(VISIBLE_COLUMNS[table]))

    def run_sql(args):
        if not isinstance(args.get("sql"), str):
            raise ToolError("run_sql needs a sql string")
        return run_sql_readonly(db_path, args["sql"])

    def calculate(args):
        try:
            tree = ast.parse(str(args.get("expression", "")), mode="eval")
            value = _eval(tree)
        except (SyntaxError, ZeroDivisionError) as e:
            raise ToolError("calculate failed: %s" % e)
        return repr(round(value, 4))

    return {"list_tables": list_tables, "describe_table": describe_table, "run_sql": run_sql, "calculate": calculate}


class ScriptedModel:
    """A stand-in for a model: returns the recorded turns in order, whatever it is shown.
    After the last turn it returns an empty string."""

    def __init__(self, turns):
        self.turns = list(turns)
        self.calls = 0

    def __call__(self, messages):
        self.calls += 1
        return self.turns[self.calls - 1] if self.calls <= len(self.turns) else ""


def tokens(text):
    """A rough token count: one token per 4 characters, rounded up."""
    return (len(text) + 3) // 4


def scripts_by_question(script_rows):
    out = {}
    for row in sorted(script_rows, key=lambda r: (r["question_id"], int(r["turn"]))):
        out.setdefault(row["question_id"], []).append(row["text"])
    return out


# ---------- the loop ----------

def parse_action(text):
    """Read one model reply. Return ("tool", name, args), ("final", answer) or ("error", message).

    A valid reply is one JSON object with either a string "final", or a string "tool" and an
    optional object "args" (default {}). Anything else is an error the model is told about.
    """
    # TODO
    raise NotImplementedError


def call_tool(tools, name, args):
    """Run one tool and return its text. Never raise: an unknown tool or a failing tool
    becomes an observation that starts with 'error: '."""
    # TODO
    raise NotImplementedError


NUMBER = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")


def numbers_in(text):
    """[(value, decimals)] for every number written in text. '1,234.50' is (1234.5, 2)."""
    out = []
    for m in NUMBER.finditer(text):
        s = m.group().replace(",", "")
        out.append((float(s), len(s.split(".")[1]) if "." in s else 0))
    return out


def ungrounded_numbers(answer, sources):
    """Numbers in answer (as written) that no source supports at the precision written.

    A number written with d decimals is supported if some number in a source rounds to it at
    d decimals. sources is a list of texts (the question and every observation).
    """
    # TODO
    raise NotImplementedError


def run_agent(question, model, tools, max_steps=8, max_repeats=3):
    """Run the loop: ask the model, act on its reply, show it the result, until it answers
    or a guard stops it.

    Return {"status", "answer", "steps", "messages"}.
    status: answered (final answer, every number grounded), ungrounded (final answer with a
    number no tool returned), stuck (the same tool call with the same args max_repeats times
    in a row; the last one is not run), step_limit (max_steps model calls and no answer).
    steps: one dict per model call: {"text", "kind" (tool, final, error, stuck), "tool",
    "args", "observation"}. messages: every message sent or received, as
    {"role": system|user|assistant|tool, "content": text}. Every tool result, and the error
    for a reply that is not a valid action, goes back to the model as a tool message.
    """
    # TODO
    raise NotImplementedError


def run_cost(messages):
    """Tokens and credits for one run. Each model call is sent every message before it
    (input) and writes its own reply (output)."""
    # TODO
    raise NotImplementedError


def budget_table(questions, scripts, tools, budgets, max_repeats=3):
    """For each max_steps in budgets: {"max_steps", "answered", "credits"} over all questions."""
    # TODO
    raise NotImplementedError


def recommend_budget(table):
    """The smallest max_steps that answers as many questions as the best budget in the table."""
    # TODO
    raise NotImplementedError


def main():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "shop.db")
        build_db(path, {"customers": load_csv("customers.csv"), "orders": load_csv("orders.csv")})
        tools = make_tools(path)
        questions = load_csv("questions.csv")
        scripts = scripts_by_question(load_csv("agent_script.csv"))
        for q in questions:
            run = run_agent(q["question"], ScriptedModel(scripts[q["question_id"]]), tools)
            cost = run_cost(run["messages"])
            print("%s %-10s %d calls %5d tokens in %4d out %5.2f credits" % (
                q["question_id"], run["status"], cost["calls"], cost["input_tokens"], cost["output_tokens"], cost["credits"]))
        table = budget_table(questions, scripts, tools, range(1, 11))
        for row in table:
            print("max_steps %2d answered %d credits %6.2f" % (row["max_steps"], row["answered"], row["credits"]))
        print("smallest budget that answers the most:", recommend_budget(table))


if __name__ == "__main__":
    main()
