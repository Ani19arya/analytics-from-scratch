"""Build the synthetic shop tables and the saved LLM queries.

Writes data/customers.csv, data/orders.csv and data/llm_queries.csv.
The LLM SQL is a saved fixture. No API is called. Run: python3 make_data.py
"""
import csv
import os
import random

random.seed(602)

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
     "SELECT o.customer_id, ROUND(SUM(o.amount), 2) AS rev FROM orders o WHERE o.status = 'completed' GROUP BY o.customer_id ORDER BY rev DESC LIMIT 3;"),
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
     "SELECT country, COUNT(order_id) FROM orders JOIN customers USING (customer_id) WHERE status = 'refunded' GROUP BY country;",
     "SELECT c.country, COUNT(*) FROM orders o JOIN customers c ON c.customer_id = o.customer_id WHERE o.status = 'refunded' GROUP BY c.country;"),
]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    with open(os.path.join(data, "customers.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["customer_id", "country"])
        for i in range(1, 61):
            w.writerow([i, random.choice(COUNTRIES)])
    with open(os.path.join(data, "orders.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["order_id", "customer_id", "order_date", "status", "amount"])
        for i in range(1, 301):
            # customers 51 to 60 never order
            cust = random.randint(1, 50)
            date = "2026-%02d-%02d" % (random.randint(1, 6), random.randint(1, 28))
            amount = round(random.uniform(5, 250), 2)
            w.writerow([i, cust, date, random.choice(STATUSES), amount])
    with open(os.path.join(data, "llm_queries.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["query_id", "question", "llm_sql", "trusted_sql"])
        w.writerows(QUERIES)
    print("wrote", data)


if __name__ == "__main__":
    main()
