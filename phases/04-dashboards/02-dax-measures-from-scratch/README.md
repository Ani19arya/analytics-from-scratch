# DAX measures from scratch

What does a Power BI measure actually compute, and how do you get the same Total Sales, filtered sales, year to date and growth on last year numbers without Power BI?

## The problem

You are the analyst at Brightwater Coffee, a roaster that sells beans, equipment and subscriptions online and in one retail shop. Femi, the finance lead, sends you a Power BI report a contractor built and asks you to check its numbers before the board pack goes out on Monday. The report has four measures: Total Sales, Online Sales, share of all categories, and Sales YTD, plus a growth on last year card. The shop was closed for a refit in March 2025, so that month has no sales at all, and Femi suspects the March 2026 growth figure is wrong. You will rebuild every measure in SQL and compare.

## What you will build from scratch

- `SUM` as a measure: one total per category.
- A `CALCULATE` style filtered measure: online sales only.
- A measure that ignores a filter (`ALL`): each category's share of all sales.
- Year to date (`TOTALYTD`) over a calendar with no gaps.
- Same period last year (`SAMEPERIODLASTYEAR`) and growth, where a missing month gives a blank, not a wrong number.

The data in `data/` is synthetic. `make_data.py` builds it with a fixed random seed: 1,191 orders from January 2025 to September 2026, with none in March 2025.

## The idea

A DAX measure is not a column. It is a formula that the engine evaluates once for every cell of a visual. Each cell comes with a **filter context**: the set of filters that apply to that cell, from its row and column headers, slicers and the page.

So a measure is a function: `measure(filters) -> number`. In SQL terms:

| DAX | What the engine does | SQL that does the same |
|---|---|---|
| `SUM(sales[amount])` in a table by category | filter the rows to one category, then add | `GROUP BY category` with `SUM(amount)` |
| `CALCULATE([Total Sales], sales[channel] = "Online")` | add a filter to the current context, then evaluate | `SUM(CASE WHEN channel = 'Online' THEN amount ELSE 0 END)` inside the same GROUP BY |
| `CALCULATE([Total Sales], ALL(sales[category]))` | remove the category filter | a subquery or `SUM(...) OVER ()` over all rows |
| `TOTALYTD([Total Sales], 'Date'[Date])` | replace the date filter with 1 January to the current date | a running sum `PARTITION BY year ORDER BY month` over a gap free calendar |
| `CALCULATE([Total Sales], SAMEPERIODLASTYEAR('Date'[Date]))` | shift the dates in the filter back one year | join each month to the month with the same number one year earlier |
| `DIVIDE(a, b)` | a / b, or blank when b is 0 or blank | `CASE WHEN b = 0 OR b IS NULL THEN NULL ELSE a / b END` |

The time intelligence rows depend on a date table with every day (lesson 01). `SAMEPERIODLASTYEAR` shifts dates on the calendar. It does not count back twelve rows. That difference is the March 2026 bug.

## Walk through

Step 1. SUM and a filtered SUM. Equipment sold 64,936.73 in total and 42,177.38 of that online.

```sql
SELECT
  category,
  ROUND(SUM(amount), 2) AS total_sales,
  ROUND(SUM(CASE WHEN channel = 'Online' THEN amount ELSE 0 END), 2) AS online_sales
FROM sales
GROUP BY category
ORDER BY category
```

You cannot use `WHERE channel = 'Online'` here, because that would also filter `total_sales`. `CALCULATE` changes the filter for one measure only, and `CASE WHEN` inside the SUM does the same.

Step 2. Remove a filter. The share needs the grand total, 115,905.51, in every row, whatever the row's category. That is what `ALL(sales[category])` gives.

```sql
SELECT
  category,
  ROUND(SUM(amount) / (SELECT SUM(amount) FROM sales), 4) AS share_of_all
FROM sales
GROUP BY category
ORDER BY category
```

Equipment is 0.5603 of all sales.

Step 3. Year to date. Build a list of every month first, so March 2025 exists with 0 sales and the running total carries through it. Then run the sum inside each year.

```sql
WITH RECURSIVE months(m) AS (
  SELECT '2025-01'
  UNION ALL
  SELECT strftime('%Y-%m', date(m || '-01', '+1 month')) FROM months WHERE m < '2026-09'
),
monthly AS (
  SELECT months.m AS year_month, COALESCE(SUM(s.amount), 0) AS sales
  FROM months LEFT JOIN sales s ON substr(s.order_date, 1, 7) = months.m
  GROUP BY months.m
)
SELECT year_month, ROUND(sales, 2) AS sales,
  ROUND(SUM(sales) OVER (PARTITION BY substr(year_month, 1, 4) ORDER BY year_month), 2) AS ytd_sales
FROM monthly
ORDER BY year_month
```

YTD is 10,695.99 at the end of February 2025, stays 10,695.99 in March, and restarts at 4,941.96 in January 2026. In the exercise, take the first and last month from the data instead of typing them.

Step 4. The trap: last year with LAG. Counting back twelve rows only works if no month is missing.

```sql
WITH m AS (SELECT substr(order_date, 1, 7) AS ym, SUM(amount) AS s FROM sales GROUP BY 1)
SELECT ym, ROUND(s, 2) AS sales, ROUND(LAG(s, 12) OVER (ORDER BY ym), 2) AS wrong_ly
FROM m
ORDER BY ym
```

Look at the 2026 rows. January gets NULL, February gets January 2025 (6,048.13), and March gets February 2025 (4,647.86). Because March 2025 has no row, every month before April is shifted by one. A growth card built on this would say March 2026 grew 21%, when there is nothing to compare it with.

Step 5. Shift the calendar instead. Join each month to the month one year earlier by date.

```sql
WITH monthly AS (SELECT substr(order_date, 1, 7) AS year_month, SUM(amount) AS sales FROM sales GROUP BY 1)
SELECT cur.year_month, ROUND(cur.sales, 2) AS sales, ROUND(COALESCE(ly.sales, 0), 2) AS sales_ly,
  CASE WHEN ly.sales IS NULL OR ly.sales = 0 THEN NULL
       ELSE ROUND((cur.sales - ly.sales) * 100.0 / ly.sales, 1) END AS growth_pct
FROM monthly cur
LEFT JOIN monthly ly ON ly.year_month = strftime('%Y-%m', date(cur.year_month || '-01', '-1 year'))
WHERE cur.year_month >= '2026-01'
ORDER BY cur.year_month
```

January 2026 is -18.3% on January 2025, February is +16.0%, and March is NULL. NULL is the honest answer: there was no March 2025 to grow from.

### The same measures in DAX (reference only, not run in this course)

These assume a `'Date'` table marked as the date table and related to `sales[order_date]`.

```dax
Total Sales = SUM ( sales[amount] )

Online Sales = CALCULATE ( [Total Sales], sales[channel] = "Online" )

Share of All = DIVIDE ( [Total Sales], CALCULATE ( [Total Sales], ALL ( sales[category] ) ) )

Sales YTD = TOTALYTD ( [Total Sales], 'Date'[Date] )

Sales LY = CALCULATE ( [Total Sales], SAMEPERIODLASTYEAR ( 'Date'[Date] ) )

Growth % = DIVIDE ( [Total Sales] - [Sales LY], [Sales LY] )
```

`DIVIDE` returns blank when `[Sales LY]` is blank, which is what the `CASE WHEN` in step 5 does. Tableau has the same ideas as table calculations: a running total restarting every year, and a year over year percent difference.

## Your turn

Open `exercise.sql` and write `sales_by_category`, `sales_ytd` and `sales_vs_last_year`.

```
python3 test_lesson.py
```

Run it from this folder. The test recomputes every measure with Python loops over the raw rows, including the month with no sales.

## Check yourself

1. What is filter context?
2. Why does `CALCULATE([Total Sales], sales[channel] = "Online")` not change the Total Sales column next to it?
3. Why does `SAMEPERIODLASTYEAR` need a date table with every day?
4. Should a growth card show 0% or blank when last year had no sales?

<details>
<summary>Answers</summary>

1. The set of filters that apply when a measure is evaluated for one cell: the row and column headers of the visual, slicers, and page and report filters. The same measure gives a different number in each cell because each cell has a different filter context.
2. CALCULATE modifies the filter context only while it evaluates its own expression. Other measures in the visual still see the original context. In SQL this is a conditional sum inside the same GROUP BY, not a WHERE clause.
3. It shifts the dates in the current filter back by one year on the calendar. If the date table had gaps, or if you counted back rows instead of dates, the shifted period would be the wrong one or would not exist.
4. Blank (NULL). Growth from nothing is undefined. 0% says sales were flat, which is false, and a huge percentage from a near zero base misleads too, so many teams also hide growth below a minimum base.

</details>

## In real job postings

On 25 October 2026 the Real Analyst Jobs live feed had 1,193 India analyst postings. Of the 914 that list tools, 39% ask for Power BI, and for data analyst titles alone it is 51%. See the [Power BI skills page](https://realanalystjobs.com/skills/power-bi) and the [Power BI vs Tableau study](https://realanalystjobs.com/research/power-bi-vs-tableau-job-postings-2026).

## Next

[03 Tableau LOD expressions in SQL](../03-tableau-lod-expressions-in-sql/)
