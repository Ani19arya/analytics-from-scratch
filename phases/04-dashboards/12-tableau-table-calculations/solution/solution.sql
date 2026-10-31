-- Lesson 12: Tableau table calculations vs LOD. Worked answer.
-- Table: sales(line_id, order_date 'YYYY-MM-DD', region, category, amount)
-- Each query is the table behind one Tableau view. Comments say which
-- Tableau calculation it stands for and where it sits in the order of operations.

-- query: running_total_by_month
-- View: region on Rows, MONTH(order_date) on Columns, SUM(amount).
-- RUNNING_SUM(SUM([Amount])), Compute Using month: addressing month, partitioning region.
-- A table calculation runs on the aggregated marks, so aggregate first, then the window.
SELECT region, year_month, ROUND(sales, 2) AS sales,
  ROUND(SUM(sales) OVER (PARTITION BY region ORDER BY year_month
                         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS running_sales
FROM (
  SELECT region, substr(order_date, 1, 7) AS year_month, SUM(amount) AS sales
  FROM sales
  GROUP BY region, year_month
) marks
ORDER BY region, year_month;

-- query: category_rank_by_region
-- View: region and category on Rows. RANK(SUM([Amount])) addressing category,
-- partitioning region. SQL RANK: ties share a rank and the next rank is skipped
-- (1, 2, 2, 4). Tableau has several rank functions; pick the one with the same tie rule.
SELECT region, category, ROUND(sales, 2) AS sales,
  RANK() OVER (PARTITION BY region ORDER BY ROUND(sales, 2) DESC) AS sales_rank
FROM (
  SELECT region, category, SUM(amount) AS sales
  FROM sales
  GROUP BY region, category
) marks
ORDER BY region, sales_rank, category;

-- query: share_with_region_filter
-- View: category on Rows, a dimension filter keeping region = 'Coast'.
-- pct_of_view: percent of total as a table calculation, after the filter: share of Coast.
-- pct_of_all_regions: SUM([Amount]) / SUM({FIXED : SUM([Amount])}). FIXED runs before
-- dimension filters, so its total is every region's sales.
SELECT category, ROUND(sales, 2) AS sales,
  ROUND(sales / SUM(sales) OVER (), 4) AS pct_of_view,
  ROUND(sales / (SELECT SUM(amount) FROM sales), 4) AS pct_of_all_regions
FROM (
  SELECT category, SUM(amount) AS sales
  FROM sales
  WHERE region = 'Coast'
  GROUP BY category
) marks
ORDER BY category;

-- query: running_total_q2
-- View: region and month, showing April to June 2026 only.
-- running_dimension_filter: the month filter is a dimension filter, so January to
--   March are gone before RUNNING_SUM runs, and the total restarts in April.
-- running_table_calc_filter: hide January to March with a table calculation filter
--   instead (it runs after table calculations), so April starts from the year's total so far.
WITH marks AS (
  SELECT region, substr(order_date, 1, 7) AS year_month, SUM(amount) AS sales
  FROM sales
  GROUP BY region, year_month
),
with_running AS (
  SELECT region, year_month, sales,
    SUM(sales) OVER (PARTITION BY region ORDER BY year_month
                     ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_all
  FROM marks
)
SELECT region, year_month, ROUND(sales, 2) AS sales,
  ROUND(SUM(sales) OVER (PARTITION BY region ORDER BY year_month
                         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS running_dimension_filter,
  ROUND(running_all, 2) AS running_table_calc_filter
FROM with_running
WHERE year_month BETWEEN '2026-04' AND '2026-06'
ORDER BY region, year_month;
