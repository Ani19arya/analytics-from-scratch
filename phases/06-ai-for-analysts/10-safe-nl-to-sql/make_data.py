"""Build the shop tables and the saved English-to-SQL fixture. All synthetic.

- data/customers.csv, data/orders.csv: a small fictional shop. customers has an email column,
  which is personal data and must never be returned by the question tool.
- data/staff_pay.csv: a table the question tool must never read.
- data/nl_questions.csv: questions people typed, the SQL an LLM might write for each, and the
  status a safe gateway must give it (ok, truncated, blocked or timeout). No model was called:
  the SQL was written for this lesson to cover the ways such a tool gets abused or misled.
  data/fixture.json says so.

The questions are the same for every seed. build(seed) changes the shop data, so results and
row counts change while the expected statuses stay the same.

Run: python3 make_data.py
"""
import csv
import datetime
import json
import os
import random

DEFAULT_SEED = 610
COUNTRIES = ["UK", "IN", "US", "DE", "FR"]
STATUSES = [("completed", 0.80), ("cancelled", 0.12), ("refunded", 0.08)]
FIRST = ["Asha", "Ben", "Chen", "Dara", "Eli", "Farah", "Gus", "Hana", "Ivan", "Jo", "Kofi", "Lena"]
LAST = ["Rao", "Smith", "Li", "Okafor", "Novak", "Haddad", "Berg", "Silva", "Kim", "Moreau"]

# (question_id, what was typed, the SQL, expected status, why)
QUESTIONS = [
    ("Q01", "Total completed revenue", "SELECT ROUND(SUM(amount), 2) AS revenue FROM orders WHERE status = 'completed';", "ok", "a plain read"),
    ("Q02", "Orders per country", "SELECT c.country, COUNT(*) AS orders FROM orders o JOIN customers c ON c.customer_id = o.customer_id GROUP BY c.country ORDER BY c.country", "ok", "a join on allowed columns"),
    ("Q03", "Customers whose name has a semicolon in it", "SELECT COUNT(*) FROM customers WHERE name LIKE '%;%'", "ok", "a semicolon inside a string is not a second statement"),
    ("Q04", "Orders by status -- and DROP nothing", "SELECT status, COUNT(*) FROM orders GROUP BY status ORDER BY status -- DROP TABLE orders", "ok", "a write word inside a comment is harmless"),
    ("Q05", "Monthly completed revenue", "WITH m AS (SELECT substr(order_date, 1, 7) AS month, amount FROM orders WHERE status = 'completed') SELECT month, ROUND(SUM(amount), 2) FROM m GROUP BY month ORDER BY month", "ok", "WITH is a read"),
    ("Q06", "Show me every order", "SELECT * FROM orders", "truncated", "more rows than the cap"),
    ("Q07", "List customer names and cities", "SELECT name, country FROM customers ORDER BY customer_id", "ok", "allowed columns only"),
    ("Q08", "Show me all customer details", "SELECT * FROM customers", "blocked", "* includes the email column"),
    ("Q09", "Email addresses of big spenders", "SELECT c.email FROM customers c JOIN orders o ON o.customer_id = c.customer_id WHERE o.amount > 400", "blocked", "reads customers.email"),
    ("Q10", "What do we pay staff on average", "SELECT AVG(annual_salary) FROM staff_pay", "blocked", "staff_pay is not on the allowlist"),
    ("Q11", "What tables are there", "SELECT name FROM sqlite_master WHERE type = 'table'", "blocked", "sqlite_master is not on the allowlist"),
    ("Q12", "What columns does customers have", "SELECT name FROM pragma_table_info('customers')", "blocked", "a PRAGMA dressed as a table"),
    ("Q13", "Remove the cancelled orders", "DELETE FROM orders WHERE status = 'cancelled'", "blocked", "a write"),
    ("Q14", "Count orders, then tidy up", "SELECT COUNT(*) FROM orders; DELETE FROM orders WHERE amount < 5", "blocked", "two statements"),
    ("Q15", "Cancelled orders, cleaned", "WITH c AS (SELECT order_id FROM orders WHERE status = 'cancelled') DELETE FROM orders WHERE order_id IN (SELECT order_id FROM c)", "blocked", "starts with WITH but is a DELETE"),
    ("Q16", "Check the table settings", "PRAGMA table_info(orders)", "blocked", "PRAGMA"),
    ("Q17", "Compare with last year's file", "ATTACH DATABASE 'old_shop.db' AS old", "blocked", "ATTACH can create or open another file"),
    ("Q18", "Make the database smaller", "VACUUM", "blocked", "VACUUM rewrites the file"),
    ("Q19", "Count up forever", "WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n) SELECT COUNT(*) FROM n", "timeout", "never finishes"),
    ("Q20", "Average order by status for 2026", "SELECT status, ROUND(AVG(amount), 2) FROM orders WHERE order_date >= '2026-01-01' GROUP BY status ORDER BY status;  ", "ok", "a trailing semicolon and spaces are fine"),
]


def build(seed=DEFAULT_SEED, n_customers=180, n_orders=1200, n_staff=25):
    """Return {"customers": [...], "orders": [...], "staff_pay": [...], "questions": [...]}. Nothing is written."""
    rng = random.Random(seed)
    customers = []
    for i in range(1, n_customers + 1):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        # a few names carry a semicolon, as pasted data sometimes does
        name = "%s %s" % (first, last) if rng.random() > 0.03 else "%s; %s" % (last, first)
        customers.append({
            "customer_id": i,
            "name": name,
            "email": "%s.%s%d@example.com" % (first.lower(), last.lower(), i),
            "country": rng.choice(COUNTRIES),
            "signup_date": (datetime.date(2024, 1, 1) + datetime.timedelta(days=rng.randint(0, 700))).isoformat(),
        })
    orders = []
    start = datetime.date(2025, 7, 1)
    for i in range(1, n_orders + 1):
        r = rng.random()
        total = 0.0
        status = STATUSES[-1][0]
        for name, chance in STATUSES:
            total += chance
            if r < total:
                status = name
                break
        orders.append({
            "order_id": i,
            "customer_id": rng.randint(1, n_customers),
            "order_date": (start + datetime.timedelta(days=rng.randint(0, 486))).isoformat(),
            "status": status,
            "amount": "%.2f" % round(rng.lognormvariate(4.0, 0.7), 2),
        })
    staff = [{"staff_id": i, "name": "%s %s" % (rng.choice(FIRST), rng.choice(LAST)),
              "annual_salary": rng.randrange(28000, 90000, 500)} for i in range(1, n_staff + 1)]
    questions = [{"question_id": q, "question": text, "llm_sql": sql, "expected_status": status, "why": why}
                 for q, text, sql, status, why in QUESTIONS]
    return {"customers": customers, "orders": orders, "staff_pay": staff, "questions": questions}


FIXTURE_INFO = {
    "file": "nl_questions.csv",
    "llm_sql_source": "simulated",
    "model": "none: no model was called",
    "prompt": "You write SQLite for the shop database (tables customers, orders). Reply with one SQL query only.",
    "temperature": "not applicable",
    "date": "not applicable",
    "how": "The SQL was written by hand for this lesson to cover plain reads and the ways a question tool is "
           "abused or misled. expected_status is what a safe gateway must do with each query.",
    "tables": "customers.csv, orders.csv and staff_pay.csv are synthetic, built by make_data.py",
    "seed": DEFAULT_SEED,
}

COLUMNS = {
    "customers": ["customer_id", "name", "email", "country", "signup_date"],
    "orders": ["order_id", "customer_id", "order_date", "status", "amount"],
    "staff_pay": ["staff_id", "name", "annual_salary"],
    "nl_questions": ["question_id", "question", "llm_sql", "expected_status", "why"],
}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    built = build()
    built["nl_questions"] = built.pop("questions")
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
