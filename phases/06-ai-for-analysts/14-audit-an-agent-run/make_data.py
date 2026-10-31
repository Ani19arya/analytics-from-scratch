"""Build three months of shop orders and SIMULATED agent run traces to audit. All synthetic.

- data/orders.csv: Larkspur Goods orders, August to October 2026. In October a payment
  outage made many more orders end as cancelled, and fewer orders came in.
- data/runs.csv: eight questions an agent answered about revenue growth between two months,
  its final answer, and what was planted in the run (the answer key): the verdict a careful
  audit must reach, the step where the run first went wrong, and the steps the answer
  depends on.
- data/run_steps.csv: every step of every run, as the agent logged it: the tool, its
  arguments as JSON, and the observation the tool returned.

No model was called. The traces were written for this lesson to look like an agent's logs:
observations come from running each step's SQL on this data, except where a problem was
planted (a recorded result that no longer matches the data). data/fixture.json says so.

Revenue at Larkspur Goods is defined as the sum of amount over orders with status
'completed', by order_date, for whole calendar months.

Run: python3 make_data.py
"""
import csv
import json
import os
import random
import sqlite3

DEFAULT_SEED = 676
PLAN = {"2026-08": (31, 430, 0.82, 0.10), "2026-09": (30, 440, 0.82, 0.10), "2026-10": (31, 405, 0.76, 0.16)}
NEXT_MONTH = {"2026-08": "2026-09", "2026-09": "2026-10", "2026-10": "2026-11"}
NAMES = {"2026-08": "August", "2026-09": "September", "2026-10": "October"}
DESCRIBE = "orders: order_id, customer_id, order_date, status, amount"

COLUMNS = {
    "orders": ["order_id", "customer_id", "order_date", "status", "amount"],
    "runs": ["run_id", "question", "month_from", "month_to", "answer", "planted_verdict", "planted_step", "depends_on", "why"],
    "run_steps": ["run_id", "step", "tool", "args", "observation"],
}


def build_orders(rng):
    orders = []
    for month, (days, n, p_completed, p_cancelled) in PLAN.items():
        for _ in range(n):
            r = rng.random()
            status = "completed" if r < p_completed else ("cancelled" if r < p_completed + p_cancelled else "refunded")
            orders.append({"order_date": "%s-%02d" % (month, rng.randint(1, days)), "status": status,
                           "amount": "%.2f" % round(rng.lognormvariate(4.0, 0.6), 2), "customer_id": rng.randint(1, 300)})
    orders.sort(key=lambda o: o["order_date"])
    return [dict(order_id=i + 1, **o) for i, o in enumerate(orders)]


def revenue_sql(month, end=None, completed=True):
    start = month + "-01"
    end = end or NEXT_MONTH[month] + "-01"
    where = "status = 'completed' AND " if completed else ""
    return "SELECT ROUND(SUM(amount), 2) FROM orders WHERE %sorder_date >= '%s' AND order_date < '%s'" % (where, start, end)


def build(seed=DEFAULT_SEED):
    """Return {"orders", "runs", "run_steps"} as lists of dicts. Nothing is written."""
    rng = random.Random(seed)
    orders = build_orders(rng)
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER, order_date TEXT, status TEXT, amount REAL)")
    conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", [[o[c] for c in COLUMNS["orders"]] for o in orders])

    def obs(sql):
        return "rows: %r" % conn.execute(sql).fetchall()

    def value(sql):
        return conn.execute(sql).fetchone()[0]

    runs, steps = [], []

    def add(run_id, month_from, month_to, sql_steps, wrong_denominator=False, final_value=None, decimals=1,
            verdict="ok", bad_step="", depends_on="", why="", extra_first=None):
        """sql_steps: [(sql, recorded_value or None)]. The calc uses the recorded values."""
        trace = [("describe_table", {"table": "orders"}, DESCRIBE)]
        if extra_first:
            trace.append(("run_sql", {"sql": extra_first}, obs(extra_first)))
        values = []
        for sql, recorded in sql_steps:
            v = value(sql) if recorded is None else recorded
            values.append(v)
            trace.append(("run_sql", {"sql": sql}, "rows: %r" % [(v,)]))
        a, b = values
        base = b if wrong_denominator else a
        expression = "(%r - %r) / %r * 100" % (b, a, base)
        calc = round((b - a) / base * 100, 4)
        trace.append(("calculate", {"expression": expression}, repr(calc)))
        shown = calc if final_value is None else final_value
        word = "grew" if shown >= 0 else "fell"
        answer = "Revenue %s %.*f%% from %s to %s." % (word, decimals, abs(shown), NAMES[month_from], NAMES[month_to])
        trace.append(("final", {"answer": answer}, ""))
        question = "How much did revenue change from %s to %s 2026?" % (NAMES[month_from], NAMES[month_to])
        runs.append({"run_id": run_id, "question": question, "month_from": month_from, "month_to": month_to, "answer": answer,
                     "planted_verdict": verdict, "planted_step": bad_step, "depends_on": depends_on, "why": why})
        for i, (tool, args, observation) in enumerate(trace, 1):
            steps.append({"run_id": run_id, "step": i, "tool": tool, "args": json.dumps(args), "observation": observation})

    sep, octo, aug = revenue_sql("2026-09"), revenue_sql("2026-10"), revenue_sql("2026-08")
    add("R1", "2026-09", "2026-10", [(sep, None), (revenue_sql("2026-10", completed=False), None)], decimals=0,
        verdict="wrong_definition", bad_step=3, depends_on="2,3,4", why="the October query counts cancelled and refunded orders")
    add("R2", "2026-08", "2026-09", [(aug, None), (sep, None)], depends_on="2,3,4", why="clean")
    add("R3", "2026-09", "2026-10", [(sep, None), (octo, None)], extra_first=revenue_sql("2026-10", completed=False),
        depends_on="3,4,5", why="clean; step 2 looked at all October orders but the answer does not use it")
    add("R4", "2026-09", "2026-10", [(sep, None), (revenue_sql("2026-10", end="2026-10-31"), None)],
        verdict="wrong_definition", bad_step=3, depends_on="2,3,4", why="the October query stops before 31 October")
    stale = round(value(aug) * 1.04, 2)
    add("R5", "2026-08", "2026-09", [(aug, stale), (sep, None)],
        verdict="replay_mismatch", bad_step=2, depends_on="2,3,4", why="the August result was recorded before late refunds were loaded")
    add("R6", "2026-09", "2026-10", [(sep, None), (octo, None)], wrong_denominator=True,
        verdict="arithmetic", bad_step=4, depends_on="2,3,4", why="divides by the later month instead of the earlier one")
    a, b = value(aug), value(sep)
    add("R7", "2026-08", "2026-09", [(aug, None), (sep, None)], final_value=round((b - a) / a * 100, 4) + 3.0,
        verdict="unsupported", bad_step=5, depends_on="", why="the final number is not the one the calculator returned")
    add("R8", "2026-08", "2026-10", [(aug, None), (octo, None)], decimals=0, depends_on="2,3,4",
        why="clean; the answer rounds to a whole percent")
    conn.close()
    return {"orders": orders, "runs": runs, "run_steps": steps}


FIXTURE_INFO = {
    "file": "run_steps.csv",
    "source": "simulated",
    "model": "none: no model was called",
    "prompt": "You are an analytics agent for the Larkspur Goods shop database. Answer the question using the tools "
              "describe_table, run_sql and calculate, then give a final answer.",
    "temperature": "not applicable",
    "date": "not applicable",
    "how": "Each trace was written for this lesson to look like an agent's step log. Observations come from running "
           "each step's SQL on the seed's data, except where a problem was planted. runs.csv records what was planted.",
    "tables": "orders.csv is synthetic, built by make_data.py",
    "seed": DEFAULT_SEED,
}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    built = build()
    for name, cols in COLUMNS.items():
        with open(os.path.join(data, name + ".csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(built[name])
    with open(os.path.join(data, "fixture.json"), "w") as f:
        json.dump(FIXTURE_INFO, f, indent=2)
        f.write("\n")
    print("wrote", data)


if __name__ == "__main__":
    main()
