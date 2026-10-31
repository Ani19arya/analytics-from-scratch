-- Lesson 02: DAX measures from scratch. Worked answer.
-- Table: sales(order_date 'YYYY-MM-DD', category, channel, amount)

-- query: sales_by_category
-- A table visual with category on rows and no slicers.
-- Total Sales = SUM(amount)
-- Online Sales = CALCULATE([Total Sales], sales[channel] = "Online"). Channel is
--   not on this visual, so the CASE WHEN inside the GROUP BY is the same thing.
-- Share = DIVIDE([Total Sales], CALCULATE([Total Sales], ALL(sales[category])))
--   ALL(category) drops only the category grouping: a window over the grouped rows.
SELECT
  category,
  ROUND(SUM(amount), 2) AS total_sales,
  ROUND(SUM(CASE WHEN channel = 'Online' THEN amount ELSE 0 END), 2) AS online_sales,
  ROUND(SUM(amount) / SUM(SUM(amount)) OVER (), 4) AS share_of_all
FROM sales
GROUP BY category
ORDER BY category;

-- query: share_with_year_slicer
-- The same visual with a Year slicer set to 2026. The slicer is a WHERE clause,
-- and ALL(sales[category]) must keep it: the window sums only the 2026 rows.
SELECT
  category,
  ROUND(SUM(amount), 2) AS total_sales,
  ROUND(SUM(amount) / SUM(SUM(amount)) OVER (), 4) AS share_of_all
FROM sales
WHERE substr(order_date, 1, 4) = '2026'
GROUP BY category
ORDER BY category;

-- query: channel_matrix
-- Channel on rows, Year slicer set to 2026.
-- online_sales: CALCULATE([Total Sales], sales[channel] = "Online") REPLACES the
--   row's channel filter, so every row shows the 2026 online total.
-- online_keepfilters: CALCULATE([Total Sales], KEEPFILTERS(sales[channel] = "Online"))
--   intersects with the row's filter: Online on the Online row, blank (NULL) on Retail.
SELECT
  channel,
  ROUND(SUM(amount), 2) AS total_sales,
  ROUND(SUM(SUM(CASE WHEN channel = 'Online' THEN amount END)) OVER (), 2) AS online_sales,
  ROUND(SUM(CASE WHEN channel = 'Online' THEN amount END), 2) AS online_keepfilters
FROM sales
WHERE substr(order_date, 1, 4) = '2026'
GROUP BY channel
ORDER BY channel;

-- query: sales_ytd
WITH RECURSIVE months(m) AS (
  SELECT MIN(substr(order_date, 1, 7)) FROM sales
  UNION ALL
  SELECT strftime('%Y-%m', date(m || '-01', '+1 month')) FROM months
  WHERE m < (SELECT MAX(substr(order_date, 1, 7)) FROM sales)
),
monthly AS (
  SELECT months.m AS year_month, COALESCE(SUM(s.amount), 0) AS sales
  FROM months
  LEFT JOIN sales s ON substr(s.order_date, 1, 7) = months.m
  GROUP BY months.m
)
SELECT
  year_month,
  ROUND(sales, 2) AS sales,
  ROUND(SUM(sales) OVER (
    PARTITION BY substr(year_month, 1, 4)
    ORDER BY year_month
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ), 2) AS ytd_sales
FROM monthly
ORDER BY year_month;

-- query: sales_vs_last_year
WITH monthly AS (
  SELECT substr(order_date, 1, 7) AS year_month, SUM(amount) AS sales
  FROM sales
  GROUP BY 1
)
SELECT
  cur.year_month,
  ROUND(cur.sales, 2) AS sales,
  ROUND(COALESCE(ly.sales, 0), 2) AS sales_ly,
  CASE WHEN ly.sales IS NULL OR ly.sales = 0 THEN NULL
       ELSE ROUND((cur.sales - ly.sales) * 100.0 / ly.sales, 1) END AS growth_pct
FROM monthly cur
LEFT JOIN monthly ly
  ON ly.year_month = strftime('%Y-%m', date(cur.year_month || '-01', '-1 year'))
WHERE cur.year_month >= '2026-01'
ORDER BY cur.year_month;
