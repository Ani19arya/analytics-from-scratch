"""Build the synthetic shop tables and the saved LLM queries.

Writes:
- data/customers.csv, data/orders.csv: database 1, the shop as it is today.
- data/db2/customers.csv, data/db2/orders.csv: database 2, built from another seed
  with the awkward rows real shops have: guest orders with no customer_id and a
  new 'pending' status. A query that is right by accident on database 1 is
  caught here.
- data/llm_queries.csv: the questions, the SQL the LLM wrote, and a trusted query.

The LLM SQL is a saved fixture, written for this lesson to show the mistakes
LLM-written SQL makes. No model was called. Run: python3 make_data.py
"""
import csv
import os
import random

DEFAULT_SEED = 602
DB2_SEED = 6020

COUNTRIES = ["US", "India", "UK", "Germany"]
STATUSES = ["completed", "completed", "completed", "refunded", "cancelled"]

QUERIES = [
    ("Q1", "Total revenue from completed orders.",
     "SELECT ROUND(SUM(amount), 2) FROM orders WHERE status = 'completed';",
     "SELECT ROUND(SUM(amount), 2) FROM orders WHERE status = 'completed';"),
    ("Q2", "Number of customers in each country.",
     "SELECT c.country, COUNT(*) FROM customers c JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.country;",
     "SELECT country, COUNT(*) FROM customers GROUP BY country;"),
    ("Q3", "Completed revenue by month.",
     "SELECT substr(order_date, 1, 7) AS month, SUM(order_total) FROM orders WHERE status = 'completed' GROUP BY month;",
     "SELECT substr(order_date, 1, 7) AS month, ROUND(SUM(amount), 2) FROM orders WHERE status = 'completed' GROUP BY month;"),
    ("Q4", "Top 3 customers by completed revenue, with their revenue.",
     "SELECT customer_id, ROUND(total, 2) FROM (SELECT customer_id, SUM(amount) AS total FROM orders WHERE status = 'completed' GROUP BY customer_id) ORDER BY total DESC LIMIT 3;",
     "SELECT o.customer_id, ROUND(SUM(o.amount), 2) AS rev FROM orders o WHERE o.status = 'completed' AND o.customer_id IS NOT NULL GROUP BY o.customer_id ORDER BY rev DESC, o.customer_id LIMIT 3;"),
    ("Q5", "Customers who have never placed an order.",
     "SELECT c.customer_id FROM customers c JOIN orders o ON o.customer_id = c.customer_id WHERE o.order_id IS NULL;",
     "SELECT c.customer_id FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id WHERE o.order_id IS NULL;"),
    ("Q6", "Average value of a completed order.",
     "SELECT ROUND(AVG(amount), 2) FROM orders;",
     "SELECT ROUND(AVG(amount), 2) FROM orders WHERE status = 'completed';"),
    ("Q7", "The 5 most recent orders.",
     "SELECT TOP 5 order_id, order_date FROM orders ORDER BY order_date DESC;",
     "SELECT order_id, order_date FROM orders ORDER BY order_date DESC, order_id DESC LIMIT 5;"),
    ("Q8", "Number of refunded orders per country.",
     "SELECT COUNT(order_id), country FROM orders JOIN customers USING (customer_id) WHERE status = 'refunded' GROUP BY country;",
     "SELECT c.country, COUNT(*) FROM orders o JOIN customers c ON c.customer_id = o.customer_id WHERE o.status = 'refunded' GROUP BY c.country;"),
    ("Q9", "Customers who have never had a completed order.",
     "SELECT customer_id FROM customers WHERE customer_id NOT IN (SELECT customer_id FROM orders WHERE status = 'completed');",
     "SELECT c.customer_id FROM customers c WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id AND o.status = 'completed');"),
    ("Q10", "How many orders were refunded or cancelled?",
     "SELECT COUNT(*) FROM orders WHERE status != 'completed';",
     "SELECT COUNT(*) FROM orders WHERE status IN ('refunded', 'cancelled');"),
    ("Q11", "Rank the countries by completed revenue, highest first.",
     "SELECT c.country, ROUND(SUM(o.amount), 2) AS revenue FROM orders o JOIN customers c ON c.customer_id = o.customer_id WHERE o.status = 'completed' GROUP BY c.country ORDER BY revenue;",
     "SELECT c.country, ROUND(SUM(o.amount), 2) AS revenue FROM orders o JOIN customers c ON c.customer_id = o.customer_id WHERE o.status = 'completed' GROUP BY c.country ORDER BY revenue DESC;"),
    ("Q12", "Delete the cancelled orders, then tell me how many orders are left.",
     "DELETE FROM orders WHERE status = 'cancelled'; SELECT COUNT(*) FROM orders;",
     "SELECT COUNT(*) FROM orders WHERE status <> 'cancelled';"),
]


def build(seed=DEFAULT_SEED, awkward=False):
    """Return {"customers": [(id, country)], "orders": [(id, customer_id, date, status, amount)]}.

    awkward=True appends rows real shops have and database 1 lacks: 3 guest orders
    (customer_id None) and 6 orders with status 'pending'.
    """
    rng = random.Random(seed)
    customers = [(i, rng.choice(COUNTRIES)) for i in range(1, 61)]
    orders = []
    for i in range(1, 301):
        # customers 51 to 60 never order
        cust = rng.randint(1, 50)
        date = "2026-%02d-%02d" % (rng.randint(1, 6), rng.randint(1, 28))
        amount = round(rng.uniform(5, 250), 2)
        orders.append((i, cust, date, rng.choice(STATUSES), amount))
    if awkward:
        extra = [None] * 3 + ["pending"] * 6
        for kind in extra:
            i = len(orders) + 1
            date = "2026-06-%02d" % rng.randint(1, 28)
            amount = round(rng.uniform(5, 250), 2)
            if kind is None:
                orders.append((i, None, date, "completed", amount))
            else:
                orders.append((i, rng.randint(1, 50), date, "pending", amount))
    return {"customers": customers, "orders": orders}


def write_tables(tables, folder):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "customers.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["customer_id", "country"])
        w.writerows(tables["customers"])
    with open(os.path.join(folder, "orders.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["order_id", "customer_id", "order_date", "status", "amount"])
        # a missing customer_id is written as an empty cell
        w.writerows(["" if v is None else v for v in row] for row in tables["orders"])


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    write_tables(build(DEFAULT_SEED), data)
    write_tables(build(DB2_SEED, awkward=True), os.path.join(data, "db2"))
    with open(os.path.join(data, "llm_queries.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["query_id", "question", "llm_sql", "trusted_sql"])
        w.writerows(QUERIES)
    print("wrote", data)


if __name__ == "__main__":
    main()
