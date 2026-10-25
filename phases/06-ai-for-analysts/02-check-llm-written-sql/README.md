# Check LLM-written SQL

Which of the queries the LLM wrote can we trust, and which ones would have put a wrong number in the report?

## The problem

Larkspur Goods, a fictional online shop, lets its managers type a question and get SQL back from an LLM. Tom, the analytics manager, wants to know how often that SQL is wrong before he lets the managers use the numbers. He saved eight questions, the SQL the LLM wrote for each, and a trusted query an analyst wrote by hand. He wants every LLM query labelled correct, wrong rows, or error by Wednesday, so he can decide whether the tool needs a human review step.

The data in `data/customers.csv`, `data/orders.csv` and `data/llm_queries.csv` is synthetic, built by `make_data.py` with a fixed random seed. No API is called: the LLM SQL is a saved fixture.

## What you will build from scratch

- A safe query runner that returns rows or an error message instead of crashing.
- A normalizer that makes two result sets comparable.
- A classifier that labels each LLM query as correct, wrong rows, or error.

## The idea

You cannot judge SQL by reading it. A query that looks plausible can still count the wrong thing. The reliable check is to run it and compare its result to a result you already trust.

Three outcomes:

1. **error**: the query does not run. Wrong column names and syntax from another SQL dialect are common. This is the safe failure, because nobody sees a number.
2. **wrong rows**: the query runs but the result differs from the trusted one. This is the dangerous failure, because it produces a believable number.
3. **correct**: the result matches.

To compare two results fairly, normalize both first:

- Round floats to 2 places, so `120.920000001` and `120.92` match.
- Sort the rows, so a different `ORDER BY` does not count as wrong. If the question is about order (a top 3 list), the trusted query and the `LIMIT` already pin which rows appear, so the set of rows is still the right test.
- Compare values only, not column names. `AS rev` versus `AS total` is not an error.

In SQL terms the comparison is a two-way set difference: `(llm EXCEPT trusted)` and `(trusted EXCEPT llm)` must both be empty. Doing it in Python with sorted lists also catches duplicate rows, which `EXCEPT` would hide.

## Walk through

Load the tables into an in-memory database. `load_db` is already written in the exercise:

```python
import exercise
conn = exercise.load_db()
print(conn.execute("SELECT COUNT(*) FROM orders").fetchall())
```

Run a query safely:

```python
import sqlite3
try:
    rows = conn.execute("SELECT TOP 5 order_id FROM orders").fetchall()
except sqlite3.Error as e:
    print("error:", e)
```

`TOP 5` is SQL Server syntax. SQLite wants `LIMIT 5`, so this raises `near "5": syntax error`.

Look at a wrong rows case side by side. The question was the number of customers in each country:

```python
print(conn.execute("SELECT country, COUNT(*) FROM customers GROUP BY country").fetchall())
print(conn.execute("SELECT c.country, COUNT(*) FROM customers c JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.country").fetchall())
```

The trusted query gives 18 for Germany. The LLM joined to orders first, so it counted orders, and gives 88. Same shape, believable number, wrong.

The worked answer prints all eight labels:

```
python3 solution/solution.py
```

Three are correct, three are wrong rows, two are errors. The subtle one is Q6, the average completed order value: the LLM forgot the status filter and returned 120.37 instead of 120.92. Nobody would catch that by eye. Q5 is the classic join mistake: an inner join can never produce a missing order, so `WHERE o.order_id IS NULL` returns nothing. It needs a `LEFT JOIN`.

## Your turn

Open `exercise.py` and fill in `run_query`, `normalize` and `classify`. Then run, from this folder:

```
python3 test_lesson.py
```

## Check yourself

1. Why is a wrong rows result worse than an error?
2. Why do you sort both results before comparing?
3. The LLM query for customers with no orders returns zero rows. What is wrong with it?
4. How would you get a trusted answer when there is none yet?

<details>
<summary>Answers</summary>

1. An error is visible and nobody uses the result. Wrong rows look like a real answer and end up in a report.
2. SQL gives no row order without `ORDER BY`, and two correct queries can order rows differently. Order is not the thing being tested.
3. It uses an inner join. An inner join only keeps customers that have an order, so filtering for a missing order can never match. A `LEFT JOIN` keeps every customer.
4. Write it yourself on a small sample you can check by hand, or check it against a number someone already reports, such as finance's revenue total.

</details>

## In real job postings

SQL is the tool these postings ask for most often. On the Real Analyst Jobs live feed read on 25 October 2026, 72% of the 2,102 US analyst postings that list tools ask for SQL, and 70% of the 914 such postings in India do. See [how to become an AI analyst](https://realanalystjobs.com/tools/how-to-become-an-ai-analyst) and the [SQL skills page](https://realanalystjobs.com/skills/sql).

## Next

[Catch made-up numbers](../03-catch-made-up-numbers/)
