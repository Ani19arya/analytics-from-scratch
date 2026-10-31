"""Build the shop tables and a SIMULATED agent script for every question. All synthetic.

- data/customers.csv, data/orders.csv: Larkspur Goods, a fictional online shop, January to
  June 2026. customers.email is personal data that the agent's SQL tool must never return.
- data/questions.csv: ten questions an analyst typed, the status a correct agent loop must end
  with (answered, ungrounded, stuck or step_limit) and why.
- data/agent_script.csv: what the "model" says at each turn, one row per turn. No model was
  called. Each turn was written for this lesson to behave like a model that uses tools: most
  scripts reach a right answer, some recover from their own mistakes, and some go wrong on
  purpose (an answer with a number no tool returned, the same call over and over, a search
  that never ends). data/fixture.json says so.

The numbers in each final answer are computed here by running the script's own SQL on the
seed's data, so a second seed gives different numbers and the same expected statuses.

Run: python3 make_data.py
"""
import csv
import datetime
import json
import os
import random
import sqlite3

DEFAULT_SEED = 613
COUNTRIES = ["DE", "FR", "IN", "UK", "US"]
FIRST = ["Asha", "Ben", "Chen", "Dara", "Eli", "Farah", "Gus", "Hana", "Ivan", "Jo", "Kofi", "Lena"]
LAST = ["Rao", "Smith", "Li", "Okafor", "Novak", "Haddad", "Berg", "Silva", "Kim", "Moreau"]
STATUSES = [("completed", 0.80), ("cancelled", 0.12), ("refunded", 0.08)]

COLUMNS = {
    "customers": ["customer_id", "name", "email", "country", "signup_date"],
    "orders": ["order_id", "customer_id", "order_date", "status", "amount"],
    "questions": ["question_id", "question", "expected_status", "why"],
    "agent_script": ["question_id", "turn", "text"],
}


def build_tables(rng, n_customers=120, n_orders=900):
    customers = []
    for i in range(1, n_customers + 1):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        customers.append({
            "customer_id": i,
            "name": "%s %s" % (first, last),
            "email": "%s.%s%d@example.com" % (first.lower(), last.lower(), i),
            "country": rng.choice(COUNTRIES),
            "signup_date": (datetime.date(2024, 1, 1) + datetime.timedelta(days=rng.randint(0, 700))).isoformat(),
        })
    orders = []
    start = datetime.date(2026, 1, 1)
    for i in range(1, n_orders + 1):
        r, total, status = rng.random(), 0.0, STATUSES[-1][0]
        for name, chance in STATUSES:
            total += chance
            if r < total:
                status = name
                break
        orders.append({
            "order_id": i,
            "customer_id": rng.randint(1, n_customers),
            "order_date": (start + datetime.timedelta(days=rng.randint(0, 180))).isoformat(),
            "status": status,
            "amount": "%.2f" % round(rng.lognormvariate(4.0, 0.7), 2),
        })
    return customers, orders


def memory_db(customers, orders):
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, name TEXT, email TEXT, country TEXT, signup_date TEXT)")
    conn.execute("CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER, order_date TEXT, status TEXT, amount REAL)")
    conn.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?)", [[c[k] for k in COLUMNS["customers"]] for c in customers])
    conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", [[o[k] for k in COLUMNS["orders"]] for o in orders])
    return conn


def tool(name, **args):
    return json.dumps({"tool": name, "args": args})


def final(text):
    return json.dumps({"final": text})


def build(seed=DEFAULT_SEED):
    """Return {"customers", "orders", "questions", "agent_script"} as lists of dicts. Nothing is written."""
    rng = random.Random(seed)
    customers, orders = build_tables(rng)
    conn = memory_db(customers, orders)

    def one(sql):
        return conn.execute(sql).fetchone()[0]

    scripts = []  # (qid, question, expected, why, [turns])

    sql = "SELECT ROUND(SUM(amount), 2) FROM orders WHERE status = 'completed' AND order_date >= '2026-03-01' AND order_date < '2026-04-01'"
    scripts.append(("Q01", "What was completed revenue in March 2026?", "answered", "one query, then the answer",
                    [tool("run_sql", sql=sql), final("Completed revenue in March 2026 was %.2f." % one(sql))]))

    sql = "SELECT country, COUNT(*) FROM customers GROUP BY country ORDER BY country"
    rows = conn.execute(sql).fetchall()
    scripts.append(("Q02", "How many customers do we have in each country?", "answered", "looks at the schema first",
                    [tool("list_tables"), tool("describe_table", table="customers"), tool("run_sql", sql=sql),
                     final("Customers by country: " + ", ".join("%s %d" % r for r in rows) + ".")]))

    sql_r = "SELECT COUNT(*) FROM orders WHERE status = 'refunded'"
    sql_n = "SELECT COUNT(*) FROM orders"
    r, n = one(sql_r), one(sql_n)
    share = round(r / n * 100, 4)
    scripts.append(("Q03", "What share of 2026 orders were refunded?", "answered", "uses the calculator for the share",
                    [tool("run_sql", sql=sql_r), tool("run_sql", sql=sql_n), tool("calculate", expression="%d / %d * 100" % (r, n)),
                     final("%.1f%% of orders were refunded (%d of %d)." % (share, r, n))]))

    sql = "SELECT COUNT(*) FROM orders WHERE status = 'cancelled'"
    broken = tool("run_sql", sql=sql)[:-1]  # the closing brace is missing: not valid JSON
    scripts.append(("Q04", "How many orders were cancelled in 2026?", "answered", "recovers from its own broken JSON",
                    [broken, tool("run_sql", sql=sql), final("%d orders were cancelled in 2026." % one(sql))]))

    sql = "SELECT ROUND(AVG(amount), 2) FROM orders WHERE status = 'completed' AND order_date >= '2026-04-01' AND order_date < '2026-07-01'"
    scripts.append(("Q05", "What was the average completed order value in Q2 2026?", "answered", "asks for a tool that does not exist, then recovers",
                    [tool("python", code="import pandas as pd"), tool("run_sql", sql=sql),
                     final("The average completed order in Q2 2026 was %.2f." % one(sql))]))

    bad = ("SELECT c.email, ROUND(SUM(o.amount), 2) AS spend FROM orders o JOIN customers c ON c.customer_id = o.customer_id "
           "WHERE o.status = 'completed' GROUP BY c.customer_id ORDER BY spend DESC, c.customer_id LIMIT 3")
    good = bad.replace("c.email", "c.name")
    rows = conn.execute(good).fetchall()
    scripts.append(("Q06", "Who are our top 3 customers by completed spend?", "answered", "the guard blocks the email column, the model asks again",
                    [tool("run_sql", sql=bad), tool("run_sql", sql=good),
                     final("Top 3 by completed spend: " + "; ".join("%s %.2f" % row for row in rows) + ".")]))

    scripts.append(("Q07", "Delete the test orders with an amount under 5.", "answered", "the write is blocked and the model says so",
                    [tool("run_sql", sql="DELETE FROM orders WHERE amount < 5"),
                     final("I cannot change data: my SQL tool is read-only. Ask the data team to remove test orders.")]))

    sql = "SELECT COUNT(*) FROM orders WHERE status = 'cancelled'"
    c = one(sql)
    completed = one("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
    wrong = round(c / completed * 100, 1)  # divided by completed orders, a number no tool returned
    scripts.append(("Q08", "What share of 2026 orders were cancelled?", "ungrounded", "the share was worked out in the model's head, against the wrong total",
                    [tool("run_sql", sql=sql), final("About %.1f%% of orders were cancelled." % wrong)]))

    sql = "SELECT COUNT(*) FROM orders WHERE customer_id = 7"
    scripts.append(("Q09", "How many orders did customer 7 place?", "stuck", "asks the same thing again and again",
                    [tool("run_sql", sql=sql)] * 6))

    wander = []
    for day in range(1, 13):
        wander.append(tool("run_sql", sql="SELECT status, COUNT(*) FROM orders WHERE order_date = '2026-05-%02d' GROUP BY status ORDER BY status" % day))
    scripts.append(("Q10", "Why did revenue drop in May?", "step_limit", "keeps looking, one day at a time, and never answers",
                    wander))
    conn.close()

    questions = [{"question_id": q, "question": text, "expected_status": status, "why": why} for q, text, status, why, _ in scripts]
    agent_script = [{"question_id": q, "turn": i + 1, "text": t} for q, _, _, _, turns in scripts for i, t in enumerate(turns)]
    return {"customers": customers, "orders": orders, "questions": questions, "agent_script": agent_script}


FIXTURE_INFO = {
    "file": "agent_script.csv",
    "source": "simulated",
    "model": "none: no model was called",
    "prompt": "You are an analytics agent for the Larkspur Goods shop database. Reply with one JSON object: "
              "{\"tool\": name, \"args\": {...}} to use a tool, or {\"final\": answer} to answer.",
    "temperature": "not applicable",
    "date": "not applicable",
    "how": "Each turn was written for this lesson to behave like a tool-using model. The numbers in final answers "
           "come from running the script's own SQL on the seed's data. Some scripts go wrong on purpose. "
           "questions.csv says what a correct loop must do with each script.",
    "tables": "customers.csv and orders.csv are synthetic, built by make_data.py",
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
