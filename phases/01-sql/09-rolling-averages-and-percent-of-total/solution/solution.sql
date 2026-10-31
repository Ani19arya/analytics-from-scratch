-- Lesson 09: rolling averages and percent of total. Worked answer.
-- Tables:
--   orders(order_id, order_date, region, amount)   no row at all on a day with no orders
--   report_period(start_date, end_date)            one row: the days the report covers
--
-- A day with no orders is a day with 0 orders, so the moving average is
-- built on a date spine (one row per calendar day). On a spine with exactly
-- one row per day, "the 6 rows before" really is "the 6 days before".

-- query: daily_orders
WITH RECURSIVE spine(day) AS (
  SELECT start_date FROM report_period
  UNION ALL
  SELECT date(day, '+1 day') FROM spine, report_period WHERE day < end_date
),
per_day AS (
  SELECT order_date, COUNT(*) AS orders, SUM(amount) AS revenue
  FROM orders
  GROUP BY order_date
)
SELECT s.day, COALESCE(p.orders, 0) AS orders, COALESCE(p.revenue, 0) AS revenue
FROM spine s
LEFT JOIN per_day p ON p.order_date = s.day
ORDER BY s.day;

-- query: moving_avg
WITH RECURSIVE spine(day) AS (
  SELECT start_date FROM report_period
  UNION ALL
  SELECT date(day, '+1 day') FROM spine, report_period WHERE day < end_date
),
daily AS (
  SELECT s.day, COUNT(o.order_id) AS orders
  FROM spine s
  LEFT JOIN orders o ON o.order_date = s.day
  GROUP BY s.day
)
SELECT day, orders,
       CASE WHEN COUNT(*) OVER w = 7 THEN ROUND(AVG(orders) OVER w, 2) END AS avg_7d
FROM daily
WINDOW w AS (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
ORDER BY day;

-- query: region_share
WITH by_region AS (
  SELECT COALESCE(o.region, 'Unassigned') AS region, SUM(o.amount) AS revenue
  FROM orders o, report_period p
  WHERE o.order_date BETWEEN p.start_date AND p.end_date
  GROUP BY COALESCE(o.region, 'Unassigned')
)
SELECT region, revenue,
       ROUND(100.0 * revenue / NULLIF(SUM(revenue) OVER (), 0), 1) AS share_pct
FROM by_region
ORDER BY revenue DESC, region;
