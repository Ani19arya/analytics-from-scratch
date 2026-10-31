-- Lesson 14: SQL dialects for work and interviews. The worked answer.
-- Each query is written so that it pins down every behaviour that differs
-- between databases: decimal division, case-insensitive matching, the day a
-- week starts on, where NULLs sort, and a tie-breaker for "the latest".
-- The SQLite-only parts are the date functions; the README shows how
-- Postgres, BigQuery and Snowflake write them.

-- query: monthly_revenue
SELECT date(ordered_at, 'start of month') AS month_start,
       COUNT(*) AS orders,
       SUM(amount) AS revenue
FROM orders
WHERE status = 'completed'
GROUP BY date(ordered_at, 'start of month')
ORDER BY month_start;

-- query: weekly_orders
-- 'weekday 0' moves forward to the next Sunday (or stays on a Sunday);
-- '-6 days' then lands on that week's Monday.
SELECT date(ordered_at, 'weekday 0', '-6 days') AS week_start,
       COUNT(*) AS orders
FROM orders
WHERE status = 'completed'
GROUP BY date(ordered_at, 'weekday 0', '-6 days')
ORDER BY week_start;

-- query: city_aov
SELECT c.city,
       COUNT(*) AS orders,
       SUM(o.amount) AS revenue,
       ROUND(1.0 * SUM(o.amount) / COUNT(*), 2) AS avg_order_value,
       ROUND(1.0 * SUM(CASE WHEN LOWER(o.promo_code) LIKE 'fest%' THEN 1 ELSE 0 END) / COUNT(*), 4) AS fest_share
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
WHERE o.status = 'completed'
GROUP BY c.city
ORDER BY c.city;

-- query: latest_order
SELECT customer_id, order_id, ordered_at, amount
FROM (
  SELECT customer_id, order_id, ordered_at, amount,
         ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY ordered_at DESC, order_id DESC) AS rn
  FROM orders
  WHERE status = 'completed'
) ranked
WHERE rn = 1
ORDER BY customer_id;

-- query: second_order_gap
WITH ranked AS (
  SELECT customer_id, date(ordered_at) AS order_date,
         ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY ordered_at, order_id) AS rn
  FROM orders
  WHERE status = 'completed'
)
SELECT f.customer_id,
       f.order_date AS first_order_date,
       CAST(julianday(s.order_date) - julianday(f.order_date) AS INTEGER) AS days_to_second
FROM ranked f
LEFT JOIN ranked s ON s.customer_id = f.customer_id AND s.rn = 2
WHERE f.rn = 1
ORDER BY days_to_second ASC NULLS LAST, f.customer_id;
