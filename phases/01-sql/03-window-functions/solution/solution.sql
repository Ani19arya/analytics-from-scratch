-- Lesson 03: window functions. Worked answer.
-- Tables:
--   monthly_revenue(region, month, revenue)   month is text 'YYYY-MM'
--   rep_sales(rep, region, sales)

-- query: running_total
-- Fiscal year to date: the data is one financial year (October to September),
-- so the total runs from each region's first month and never restarts in January.
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

-- query: rep_rank
SELECT
  region,
  rep,
  sales,
  RANK() OVER (PARTITION BY region ORDER BY sales DESC) AS sales_rank,
  ROW_NUMBER() OVER (PARTITION BY region ORDER BY sales DESC, rep ASC) AS row_num
FROM rep_sales
ORDER BY region, row_num;

-- query: top_reps
SELECT region, rep
FROM (
  SELECT region, rep, RANK() OVER (PARTITION BY region ORDER BY sales DESC) AS sales_rank
  FROM rep_sales
) ranked
WHERE sales_rank = 1
ORDER BY region, rep;

-- query: month_over_month
SELECT
  region,
  month,
  revenue,
  LAG(revenue) OVER (PARTITION BY region ORDER BY month) AS prev_revenue,
  revenue - LAG(revenue) OVER (PARTITION BY region ORDER BY month) AS change
FROM monthly_revenue
ORDER BY region, month;

-- query: rep_cumulative
-- The tie breaker (rep) and the ROWS frame give each rep their own running value.
-- With ORDER BY sales DESC alone, the default RANGE frame adds tied reps together.
SELECT
  region,
  rep,
  sales,
  SUM(sales) OVER (
    PARTITION BY region
    ORDER BY sales DESC, rep
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) AS cumulative_sales
FROM rep_sales
ORDER BY region, sales DESC, rep;
