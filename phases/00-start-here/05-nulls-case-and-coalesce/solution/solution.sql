-- Lesson 00-05: NULLs, CASE and COALESCE. Worked answer.
-- Table:
--   orders(order_id, order_date, city, status, amount, delivered_date, tip)

-- query: delivery_date_counts
SELECT
  COUNT(*) AS total_orders,
  COUNT(delivered_date) AS with_date,
  COUNT(*) - COUNT(delivered_date) AS without_date
FROM orders;

-- query: orders_without_delivery_date
SELECT order_id, status
FROM orders
WHERE delivered_date IS NULL
ORDER BY order_id;

-- query: order_sizes
SELECT
  order_id,
  amount,
  CASE
    WHEN amount IS NULL THEN 'unknown'
    WHEN amount < 300 THEN 'small'
    WHEN amount < 800 THEN 'medium'
    ELSE 'large'
  END AS size
FROM orders
ORDER BY order_id;

-- query: size_counts
SELECT
  SUM(CASE WHEN amount < 300 THEN 1 ELSE 0 END) AS small,
  SUM(CASE WHEN amount >= 300 AND amount < 800 THEN 1 ELSE 0 END) AS medium,
  SUM(CASE WHEN amount >= 800 THEN 1 ELSE 0 END) AS large,
  SUM(CASE WHEN amount IS NULL THEN 1 ELSE 0 END) AS unknown
FROM orders;

-- query: tip_summary
SELECT
  COUNT(tip) AS tips_recorded,
  ROUND(AVG(tip), 2) AS avg_tip_recorded,
  ROUND(AVG(COALESCE(tip, 0)), 2) AS avg_tip_blank_as_zero
FROM orders;
