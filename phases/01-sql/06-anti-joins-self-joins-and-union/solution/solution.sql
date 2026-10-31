-- Lesson 06: anti-joins, self-joins and UNION. Worked answer.
-- Tables:
--   customers(customer_id, name, city, referred_by)   referred_by is a customer_id or NULL
--   web_orders(order_id, customer_id, order_date, amount)   customer_id is NULL for a guest checkout
--   app_orders(order_id, customer_id, order_date, amount)
-- The two order tables come from two systems that both number orders from 1,
-- so stack them with UNION ALL: UNION would merge rows that happen to match.

-- query: monthly_orders
WITH all_orders AS (
  SELECT order_id, customer_id, order_date, amount FROM web_orders
  UNION ALL
  SELECT order_id, customer_id, order_date, amount FROM app_orders
)
SELECT
  strftime('%Y-%m', order_date) AS month,
  COUNT(*) AS orders,
  ROUND(SUM(amount), 2) AS revenue
FROM all_orders
GROUP BY month
ORDER BY month;

-- query: lapsed_customers
WITH all_orders AS (
  SELECT customer_id, order_date FROM web_orders
  UNION ALL
  SELECT customer_id, order_date FROM app_orders
)
SELECT c.customer_id, c.name, r.name AS referrer_name
FROM customers c
LEFT JOIN customers r ON r.customer_id = c.referred_by   -- self-join: r is the referrer
WHERE EXISTS (
    SELECT 1 FROM all_orders o
    WHERE o.customer_id = c.customer_id
      AND o.order_date >= '2026-03-01' AND o.order_date < '2026-04-01'
  )
  AND NOT EXISTS (
    SELECT 1 FROM all_orders o
    WHERE o.customer_id = c.customer_id
      AND o.order_date >= '2026-04-01' AND o.order_date < '2026-05-01'
  )
ORDER BY c.customer_id;

-- query: march_april_summary
WITH all_orders AS (
  SELECT customer_id, order_date FROM web_orders
  UNION ALL
  SELECT customer_id, order_date FROM app_orders
),
march AS (
  SELECT DISTINCT customer_id FROM all_orders
  WHERE order_date >= '2026-03-01' AND order_date < '2026-04-01' AND customer_id IS NOT NULL
),
april AS (
  SELECT DISTINCT customer_id FROM all_orders
  WHERE order_date >= '2026-04-01' AND order_date < '2026-05-01' AND customer_id IS NOT NULL
)
SELECT
  (SELECT COUNT(*) FROM march) AS march_customers,
  (SELECT COUNT(*) FROM april) AS april_customers,
  (SELECT COUNT(*) FROM march m JOIN april a ON a.customer_id = m.customer_id) AS both_months,
  (SELECT COUNT(*) FROM march m WHERE NOT EXISTS (SELECT 1 FROM april a WHERE a.customer_id = m.customer_id)) AS march_only,
  (SELECT COUNT(*) FROM (SELECT customer_id FROM march UNION SELECT customer_id FROM april)) AS either_month;
