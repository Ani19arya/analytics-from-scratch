# Window functions

How is each region tracking against its year to date, who are the top reps, and did revenue go up or down from last month?

## The problem

You are the sales analyst at Fernhill Supply, a wholesale company with three regions. Priya, the head of sales, opens the monthly review on Thursday and wants three things on one sheet: a running total of revenue per region, a ranked list of reps inside each region, and the change from the previous month. Last quarter someone built the rep ranking with ROW_NUMBER, and one of two tied reps was left off the bonus list. You have 12 months of revenue for each region and the sales total for 15 reps.

## What you will build from scratch

- A running total with `SUM(...) OVER (PARTITION BY ... ORDER BY ...)`.
- A rep ranking with both `RANK()` and `ROW_NUMBER()`, so you can see where they differ.
- A top-rep list that keeps ties.
- A month over month comparison with `LAG()`.

The data in `data/` is synthetic. `make_data.py` builds it with a fixed random seed.

## The idea

GROUP BY collapses many rows into one. A window function keeps every row and adds a column computed from a set of related rows, called the window.

```
function(...) OVER (
  PARTITION BY region      -- which rows belong together (like GROUP BY, but no collapse)
  ORDER BY month           -- the order inside each partition
  ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW   -- which rows of the partition to use
)
```

- **Running total.** For row i in a partition, running_total_i = revenue_1 + revenue_2 + ... + revenue_i. The frame `UNBOUNDED PRECEDING AND CURRENT ROW` says exactly that.
- **ROW_NUMBER** numbers the rows 1, 2, 3, ... with no repeats. If two rows tie, the database picks an order unless you add a tie breaker.
- **RANK** gives tied rows the same number and then skips. Sales of 60, 60, 55, 55, 50 get ranks 1, 1, 3, 3, 5. ROW_NUMBER gives 1, 2, 3, 4, 5.
- **LAG(x)** returns x from the previous row in the partition order. The first row has no previous row, so it gets NULL.

Window functions are computed after WHERE and GROUP BY. That is why you cannot filter on them in the same query's WHERE clause, and you wrap them in a subquery instead.

## Walk through

Step 1. The running total. North starts at 36518, then adds 34453 to reach 70971, then adds 40584 to reach 111555.

```sql
SELECT
  region,
  month,
  revenue,
  SUM(revenue) OVER (
    PARTITION BY region
    ORDER BY month
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) AS running_total
FROM monthly_revenue
ORDER BY region, month;
```

The partition restarts the sum at each region. Without `PARTITION BY region` the total would run across all three regions.

Step 2. Rank the reps. In North, R04 and R05 both sold 60000.

```sql
SELECT
  region,
  rep,
  sales,
  RANK() OVER (PARTITION BY region ORDER BY sales DESC) AS sales_rank,
  ROW_NUMBER() OVER (PARTITION BY region ORDER BY sales DESC, rep ASC) AS row_num
FROM rep_sales
ORDER BY region, row_num;
```

North comes out as R04 and R05 at rank 1, R02 and R03 at rank 3, and R01 at rank 5. ROW_NUMBER runs 1 to 5.

Step 3. Keep every top rep. Filtering `row_num = 1` would drop R05. Filter on the rank instead, in an outer query.

```sql
SELECT region, rep
FROM (
  SELECT region, rep, RANK() OVER (PARTITION BY region ORDER BY sales DESC) AS sales_rank
  FROM rep_sales
) ranked
WHERE sales_rank = 1
ORDER BY region, rep;
```

Step 4. Compare with the previous month. North went from 36518 to 34453, a change of -2065.

```sql
SELECT
  region,
  month,
  revenue,
  LAG(revenue) OVER (PARTITION BY region ORDER BY month) AS prev_revenue,
  revenue - LAG(revenue) OVER (PARTITION BY region ORDER BY month) AS change
FROM monthly_revenue
ORDER BY region, month;
```

The month column is text in `YYYY-MM` form, which sorts in date order. A format like `Oct 2025` would not.

## Your turn

Open `exercise.sql` and write `running_total`, `rep_rank`, `top_reps` and `month_over_month`.

```
python3 test_lesson.py
```

Run it from this folder. The test recomputes every answer with a Python loop.

## Check yourself

1. When would you use ROW_NUMBER instead of RANK?
2. What does DENSE_RANK give for sales of 60, 60, 55?
3. Why can you not write `WHERE RANK() OVER (...) = 1`?
4. A month is missing for one region. What does LAG return for the month after the gap?

<details>
<summary>Answers</summary>

1. When you need exactly one row per group, such as the latest order per customer for deduplication. Add a tie breaker to the ORDER BY so the result is repeatable.
2. 1, 1, 2. DENSE_RANK does not skip numbers after a tie.
3. WHERE runs before window functions are computed. Compute the rank in a subquery or CTE and filter in the outer query.
4. The revenue of the last month that exists, which is two months back. LAG looks at the previous row, not the previous calendar month. Fill missing months first if the comparison must be calendar based.

</details>

## In real job postings

On 25 October 2026 the Real Analyst Jobs live feed had 1,193 India analyst postings, and 70% of the 914 that list tools ask for SQL. See the roles on the [SQL skills page](https://realanalystjobs.com/skills/sql).

## Next

[04 Cohort retention](../04-cohort-retention/)
