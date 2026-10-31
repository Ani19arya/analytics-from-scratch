-- Lesson 12: review a query someone else wrote. Worked answer.
-- Tables:
--   customers(customer_id, city)
--   orders(order_id, customer_id, ordered_at, amount, status)    one row per order
--   order_items(order_id, line_no, item, qty)                    one row per item line
--   promo_redemptions(order_id, promo_code, channel)              at most one row per order
--
-- What was wrong with slide_query.sql, and the fix for each:
--   FANOUT            joining order_items repeats each order once per item line, so
--                     SUM(o.amount) counts an order's amount once per line.
--                     Fix: add up the items per order first, then join one row per order.
--   LEFT_JOIN_FILTER  p.channel <> 'staff' in WHERE is NULL for orders with no promo,
--                     so it removes every order without a promo code.
--                     Fix: keep the rows where p.channel IS NULL as well.
--   INTEGER_DIVISION  whole number / whole number drops the decimals in SQLite.
--                     Fix: 1.0 * before dividing, round only for display.
--   DATE_BOUND        BETWEEN '2026-10-01' AND '2026-10-31' stops at 31 October
--                     00:00:00, so it misses the whole of 31 October.
--                     Fix: >= '2026-10-01' AND < '2026-11-01'.

-- query: fixed_slide
WITH items AS (
  SELECT order_id, SUM(qty) AS items
  FROM order_items
  GROUP BY order_id
),
october AS (
  SELECT o.order_id, c.city, o.amount, COALESCE(i.items, 0) AS items
  FROM orders o
  JOIN customers c ON c.customer_id = o.customer_id
  LEFT JOIN items i ON i.order_id = o.order_id
  LEFT JOIN promo_redemptions p ON p.order_id = o.order_id
  WHERE o.status = 'completed'
    AND o.ordered_at >= '2026-10-01' AND o.ordered_at < '2026-11-01'
    AND (p.channel IS NULL OR p.channel <> 'staff')
)
SELECT city,
       COUNT(*) AS orders,
       SUM(items) AS items,
       SUM(amount) AS revenue,
       ROUND(1.0 * SUM(amount) / COUNT(*), 2) AS avg_order_value,
       ROUND(1.0 * SUM(items) / COUNT(*), 2) AS items_per_order
FROM october
GROUP BY city
ORDER BY revenue DESC, city;

-- query: findings
SELECT 'FANOUT' AS bug_code
UNION ALL SELECT 'LEFT_JOIN_FILTER'
UNION ALL SELECT 'INTEGER_DIVISION'
UNION ALL SELECT 'DATE_BOUND';
