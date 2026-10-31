# SQL from raw tables

This phase teaches the SQL an analyst writes every day, starting from one raw table and ending with the queries interviewers use to separate juniors from seniors: grouping and totals, joins that neither drop nor double count rows, window functions, and cohort retention. Each lesson has a business problem with a named stakeholder, a small synthetic dataset, and a trap that gives a plausible wrong number, shown failing on the lesson's own data. You prove every answer twice: once in SQL, and once in a plain Python loop inside the test. Each lesson follows the course format in [LESSON_TEMPLATE.md](../../LESSON_TEMPLATE.md).

## Who it is for

- Beginners who can open a terminal and want SQL that holds up at work. Lesson 01 explains SELECT, FROM and WHERE in a short box, so you can start there with no SQL at all.
- Spreadsheet users who already think in filters and pivot tables and want the same in SQL.
- Anyone preparing for an analyst interview: the Common mistakes and Check yourself sections are the questions interviewers ask.

You need Python 3.9 or later. SQLite comes with Python, so there is nothing to install and nothing to connect to. The two start-here lessons that will come before this phase, 00-04 Your first SQL query (planned) and 00-05 NULLs, CASE and COALESCE (planned), are not written yet; lessons 01 and 02 cover what you need from them.

## Lessons, in learning order

Folder numbers stay fixed because they are live links; the list below is the order to take them in. Planned lessons are listed so you can see where the phase is going; they have no folder yet.

**Level 1: beginner**

1. [01 GROUP BY from raw rows](01-group-by-from-raw-rows/): completed revenue by city with COUNT, SUM and AVG, HAVING versus WHERE, and the logical order a query runs in.
2. 05 Dates and the date spine (planned): signups per day, including the days with zero.
3. [02 Joins without losing rows](02-joins-without-losing-rows/): predict a join's row count, find customers who never ordered (LEFT JOIN and NOT EXISTS), and fix a fan-out that overstated revenue.
4. 06 Anti-joins, self-joins and UNION (planned): which customers ordered in March but not in April?
5. 07 Subqueries and CTEs (planned): which customers spent more than their city's average?

**Level 2: intermediate**

6. 08 Duplicates and reconciliation (planned): after the CRM import doubled some rows, how many unique customers really signed up?
7. [03 Window functions](03-window-functions/): fiscal year to date running totals, RANK versus ROW_NUMBER for a bonus list, LAG for month over month, and the ROWS versus RANGE frame trap.
8. 09 Rolling averages and percent of total (planned): the 7-day moving average of orders, and each region's share of revenue.
9. 10 Sessionization from raw events (planned): sessions per user with a 30-minute timeout.
10. 11 Gaps and islands: streaks (planned): which users logged a workout three days in a row?
11. [04 Cohort retention](04-cohort-retention/): monthly signup cohorts, retention by month since signup, and a triangle that keeps real zeros as 0 and unobserved months blank.
12. 12 Review a query someone else wrote (planned): a teammate, or an assistant, wrote this query. Is the number on the slide right?

**Level 3: advanced**

13. 13 Query plans and indexes (planned): why does the dashboard query take 40 seconds?
14. 14 SQL dialects for work and interviews (planned): the same five queries in SQLite, Postgres, BigQuery and Snowflake.

## How to run a lesson

```
cd phases/01-sql/01-group-by-from-raw-rows
python3 test_lesson.py                      # fails until your exercise.sql is right
CHECK_SOLUTION=1 python3 test_lesson.py     # shows the worked solution passing
python3 make_data.py                        # rebuilds data/ exactly as committed
```

Every test checks your queries on the committed data, on a second dataset built with another seed, and on tiny hand-made tables for the edge cases (no rows, a tie, a NULL, a zero). A query that types out the answers will not pass.

**How to run a single query.** From inside a lesson folder, the runner in this folder loads every CSV in `data/` as a table and prints the result:

```
python3 ../query.py "SELECT status, COUNT(*) AS orders FROM orders GROUP BY status"
python3 ../query.py scratch.sql
```

`../query.py` is the shortcut for use inside a lesson folder. From the repo root, [tools/query.py](../../tools/query.py) does the same for any lesson: `python3 tools/query.py phases/01-sql/01-group-by-from-raw-rows "SELECT ..."`.

Use the second form for a query longer than one line: save it in a file, then run the file. Empty cells print as `NULL`, so you can tell a missing value from a 0.

## SQLite and other databases

The lessons use SQLite because it needs no setup. The ideas carry over unchanged; a few spellings do not.

| In these lessons (SQLite) | Postgres | BigQuery | Snowflake |
|---|---|---|---|
| `strftime('%Y-%m', d)` (lesson 04) | `TO_CHAR(d, 'YYYY-MM')` or `DATE_TRUNC('month', d)` | `FORMAT_DATE('%Y-%m', d)` or `DATE_TRUNC(d, MONTH)` | `TO_CHAR(d, 'YYYY-MM')` or `DATE_TRUNC('month', d)` |
| Calendar months between two dates, built from year * 12 + month (lesson 04) | `(EXTRACT(YEAR FROM e) - EXTRACT(YEAR FROM s)) * 12 + EXTRACT(MONTH FROM e) - EXTRACT(MONTH FROM s)`; not `AGE()`, which counts by day of month | `DATE_DIFF(e, s, MONTH)` | `DATEDIFF('month', s, e)` |
| `substr(month, 1, 4)` (lesson 03) | `SUBSTRING(month, 1, 4)` or `substr` | `SUBSTR(month, 1, 4)` | `SUBSTR(month, 1, 4)` |
| `SUM(x > 50)` counts rows where the comparison is true, because SQLite turns true and false into 1 and 0 | `SUM(CASE WHEN x > 50 THEN 1 ELSE 0 END)`, or `COUNT(*) FILTER (WHERE x > 50)` | `COUNTIF(x > 50)`; `SUM` of a true/false value is an error | `COUNT_IF(x > 50)` or the CASE form |
| Window filter in an outer query (lesson 03) | Same | `QUALIFY` also works | `QUALIFY` also works |

`SUM(CASE WHEN ... THEN 1 ELSE 0 END)` runs everywhere, so it is the safe form when you are not sure where a query will run. These lessons use the CASE form and never `SUM` over a comparison.

Four behaviours that differ and can change a number without an error:

- **Integer division.** `24 / 42` is 0 in SQLite, Postgres and SQL Server, and about 0.571 in BigQuery and Snowflake. Write `100.0 * a / b` to be safe everywhere.
- **NULL in ORDER BY.** SQLite sorts NULL first in ascending order; Postgres and Snowflake sort it last. Write `NULLS FIRST` or `NULLS LAST` where it matters.
- **Lenient SQLite.** SQLite accepts a SELECT alias in WHERE (Snowflake does too; Postgres, SQL Server and BigQuery do not) and a column that is neither grouped nor aggregated in a GROUP BY query (Postgres, SQL Server, BigQuery and Snowflake all reject it). See lesson 01.
- **RIGHT and FULL OUTER JOIN** need SQLite 3.39 or later. The exercises do not use them.

Previous: start here, phase 00 (planned). Next phase: [02 Statistics and experiments](../02-statistics-and-experiments/).
