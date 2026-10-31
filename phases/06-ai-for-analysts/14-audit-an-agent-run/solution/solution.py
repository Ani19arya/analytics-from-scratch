"""Solution: audit an agent's logged run. Trace each number in its answer back to the steps
that produced it, then check only those steps: replay, definition, arithmetic."""
import csv
import json
import os
import pathlib
import re
import sqlite3

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CONSTANTS = {100.0}  # numbers a calculation may use without a source (per cent)

# ---------- given: loading, the database, small helpers ----------

SCHEMA = "CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER, order_date TEXT, status TEXT, amount REAL)"


def load_csv(name, data_dir=DATA):
    with open(os.path.join(data_dir, name), newline="") as f:
        return list(csv.DictReader(f))


def steps_by_run(rows):
    """{run_id: [step dicts in order]} with step as int and args parsed from JSON."""
    out = {}
    for r in sorted(rows, key=lambda r: (r["run_id"], int(r["step"]))):
        out.setdefault(r["run_id"], []).append({"step": int(r["step"]), "tool": r["tool"],
                                                "args": json.loads(r["args"]), "observation": r["observation"]})
    return out


def build_db(path, orders):
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    conn.execute(SCHEMA)
    cols = ["order_id", "customer_id", "order_date", "status", "amount"]
    conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", [[o[c] for c in cols] for o in orders])
    conn.commit()
    conn.close()


def open_readonly(path):
    conn = sqlite3.connect(pathlib.Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    conn.execute("PRAGMA query_only = ON")
    return conn


NUMBER = re.compile(r"-?\d+(?:,\d{3})*(?:\.\d+)?")


def numbers_in(text):
    """[(text, value, decimals)] for every number written in text. '-1,234.50' is ('-1,234.50', -1234.5, 2)."""
    out = []
    for m in NUMBER.finditer(text):
        s = m.group().replace(",", "")
        out.append((m.group(), float(s), len(s.split(".")[1]) if "." in s else 0))
    return out


def month_of(sql):
    """The month of the first date literal in sql, such as '2026-10'. '' if there is none."""
    m = re.search(r"'(\d{4}-\d{2})-\d{2}'", sql)
    return m.group(1) if m else ""


def next_month(month):
    year, mon = int(month[:4]), int(month[5:7])
    return "%04d-%02d" % (year + mon // 12, mon % 12 + 1)


def step_text(step):
    """What a step showed: its observation, or for a final step its answer."""
    return step["args"].get("answer", "") if step["tool"] == "final" else step["observation"]


# ---------- the audit ----------

def supports(observation, value, decimals):
    """True if some number in observation, rounded to decimals, equals value (signs ignored:
    an answer says 'fell 11.7%' where the calculator says -11.7)."""
    return any(round(abs(v), decimals) == round(abs(value), decimals) for _, v, _ in numbers_in(observation))


def trace_lineage(steps):
    """Which steps does the final answer depend on?

    Start from every number in the final answer. For each, find the most recent earlier step
    whose observation supports it at the precision written. If that step is a calculate step,
    do the same for every distinct number in its expression (except CONSTANTS). Return
    {"depends_on": sorted step numbers, "unsupported": [(step number, number text)]}: the
    numbers no earlier step supports, with the step they appear in.
    """
    finals = [s for s in steps if s["tool"] == "final"]
    if not finals:
        return {"depends_on": [], "unsupported": []}
    final = finals[-1]
    todo = [(final["step"], text, value, d) for text, value, d in numbers_in(step_text(final))]
    depends, unsupported = set(), []
    while todo:
        at, text, value, d = todo.pop(0)
        source = None
        for s in sorted(steps, key=lambda s: -s["step"]):
            if s["step"] < at and s["tool"] != "final" and supports(s["observation"], value, d):
                source = s
                break
        if source is None:
            unsupported.append((at, text))
            continue
        if source["step"] in depends:
            continue
        depends.add(source["step"])
        if source["tool"] == "calculate":
            seen = set()
            for t, v, dd in numbers_in(source["args"].get("expression", "")):
                if abs(v) not in CONSTANTS and t not in seen:
                    seen.add(t)
                    todo.append((source["step"], t, v, dd))
    return {"depends_on": sorted(depends), "unsupported": unsupported}


def replay_matches(conn, step):
    """Run the step's SQL again and compare with what the agent logged, as text."""
    try:
        now = "rows: %r" % conn.execute(step["args"]["sql"]).fetchall()
    except sqlite3.Error:
        return False
    return now == step["observation"]


def reference_revenue(conn, month):
    """Revenue for a whole month by the company definition: sum of amount over completed
    orders with order_date in that month, rounded to 2 decimals. 0.0 for a month with none."""
    value = conn.execute(
        "SELECT ROUND(SUM(amount), 2) FROM orders WHERE status = 'completed' AND order_date >= ? AND order_date < ?",
        (month + "-01", next_month(month) + "-01")).fetchone()[0]
    return 0.0 if value is None else value


def correct_growth(conn, month_from, month_to):
    """Revenue growth in per cent from month_from to month_to, rounded to 1 decimal.
    None when month_from has no revenue."""
    a, b = reference_revenue(conn, month_from), reference_revenue(conn, month_to)
    if a == 0:
        return None
    return round((b - a) / a * 100, 1)


def audit_run(conn, run, steps):
    """Audit one run. Check only the steps the answer depends on, in step order:

    run_sql:   replay_mismatch if rerunning it gives another result than the one logged,
               else wrong_definition if its number differs from reference_revenue for the
               month of its first date literal
    calculate: arithmetic if its result differs (at 4 decimals) from (b - a) / a * 100, where
               a and b are the values of the run_sql steps it depends on, earlier month first
    any step:  unsupported if a number in it has no source (see trace_lineage)

    The verdict is the problem at the earliest step (unsupported first if one step has two);
    no_answer if there is no final step; ok
    if nothing fails. Return {"run_id", "verdict", "bad_step" (int or None), "checked_steps",
    "correct"} where correct is correct_growth for the run's two months.
    """
    lineage = trace_lineage(steps)
    result = {"run_id": run["run_id"], "verdict": "ok", "bad_step": None, "checked_steps": lineage["depends_on"],
              "correct": correct_growth(conn, run["month_from"], run["month_to"])}
    if not any(s["tool"] == "final" for s in steps):
        result["verdict"] = "no_answer"
        return result
    by_step = {s["step"]: s for s in steps}
    issues = [(at, "unsupported") for at, _ in lineage["unsupported"]]
    sql_steps = [by_step[n] for n in lineage["depends_on"] if by_step[n]["tool"] == "run_sql"]
    for n in lineage["depends_on"]:
        s = by_step[n]
        if s["tool"] == "run_sql":
            if not replay_matches(conn, s):
                issues.append((n, "replay_mismatch"))
                continue
            found = numbers_in(s["observation"])
            if not found or round(found[0][1], 2) != reference_revenue(conn, month_of(s["args"]["sql"])):
                issues.append((n, "wrong_definition"))
        elif s["tool"] == "calculate":
            inputs = sorted((month_of(q["args"]["sql"]), numbers_in(q["observation"])[0][1]) for q in sql_steps if q["step"] < n)
            ok = False
            if len(inputs) == 2 and inputs[0][1] != 0:
                a, b = inputs[0][1], inputs[1][1]
                ok = abs(float(s["observation"]) - round((b - a) / a * 100, 4)) < 1e-9
            if not ok:
                issues.append((n, "arithmetic"))
    if issues:
        order = ["unsupported", "replay_mismatch", "wrong_definition", "arithmetic"]
        result["bad_step"], result["verdict"] = min(issues, key=lambda i: (i[0], order.index(i[1])))
    return result


def audit_all(conn, runs, steps):
    """audit_run for every run, in the order of runs. steps is {run_id: [steps]}."""
    return [audit_run(conn, run, steps.get(run["run_id"], [])) for run in runs]


def main():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "shop.db")
        build_db(path, load_csv("orders.csv"))
        conn = open_readonly(path)
        runs = load_csv("runs.csv")
        steps = steps_by_run(load_csv("run_steps.csv"))
        total = checked = 0
        for run, result in zip(runs, audit_all(conn, runs, steps)):
            total += len(steps[run["run_id"]])
            checked += len(result["checked_steps"])
            print("%s %-16s step %-4s checked %-9s correct %6.1f%% | %s" % (
                run["run_id"], result["verdict"], result["bad_step"], ",".join(map(str, result["checked_steps"])) or "-",
                result["correct"], run["answer"]))
        conn.close()
        print("steps logged:", total, "| steps the answers depend on:", checked)


if __name__ == "__main__":
    main()
