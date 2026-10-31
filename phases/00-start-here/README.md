# Phase 00: Start here

Six short lessons for complete beginners. If you have never written code or a database query, start with lesson 01 and go in order.

## Who this phase is for

- You want to become a data, business or product analyst and are starting from zero.
- You use spreadsheets but have never used Python or SQL.
- You have tried a course before and got stuck at "open a terminal" or "install this".

If you can already write a SELECT with WHERE and ORDER BY and a Python loop over a CSV, skip to [phase 01](../01-sql/01-group-by-from-raw-rows/).

## What you need

- A computer with Windows, macOS or Linux.
- Python 3.9 or later. [Lesson 01](01-run-your-first-lesson/) shows how to check and, if needed, install it from the official page, https://www.python.org/downloads/ .
- Nothing else to install. Every lesson runs offline with Python and the SQLite database that comes with it. No accounts, no keys.

## The lessons

Every lesson has a business question, a small synthetic dataset, an exercise that fails until your answer is right, and a test that checks it. Each is Level 1.

| # | Lesson | Time | What you learn |
|---|---|---|---|
| 01 | [Run your first lesson](01-run-your-first-lesson/) | 1 h | Check Python, open a terminal, run a test, read a failure, fix it and see it pass |
| 02 | [Think like an analyst](02-think-like-an-analyst/) | 2 h | Turn "sales are down" into a clear question, a metric, a fair comparison and a split by segment |
| 03 | [Tables, rows and grain](03-tables-rows-and-grain/) | 1.5 h | What one row means, primary keys, one-to-many, and why the wrong grain double counts |
| 04 | [Your first SQL query](04-your-first-sql-query/) | 2 h | SELECT, FROM, WHERE, ORDER BY, LIMIT, AND and OR, and running SQL on any lesson with `tools/query.py` |
| 05 | [NULLs, CASE and COALESCE](05-nulls-case-and-coalesce/) | 2 h | Missing values, IS NULL, COUNT(*) against COUNT(column), buckets with CASE |
| 06 | [Python for spreadsheet people](06-python-for-spreadsheet-people/) | 3 h | Values, lists, dicts, loops, functions, reading a CSV, and your own SUM, COUNT and SUMIF |

About 11.5 hours in total.

## How to run SQL on any lesson

From the top folder of the course:

```
python3 tools/query.py <lesson-folder> "<SQL>"
```

For example `python3 tools/query.py phases/00-start-here/04-your-first-sql-query "SELECT * FROM orders LIMIT 5"`. It loads the lesson's CSV files into a temporary SQLite database and prints the result. Lesson 04 explains it.

## Where to go next

- [Phase 01, lesson 01: GROUP BY from raw rows](../01-sql/01-group-by-from-raw-rows/), the next step in SQL.
- The [learning roadmap](../../LEARNING_ROADMAP.md), for the full order across SQL, statistics, metrics, dashboards, Python and AI, and the milestones that show what you can do at each level.
