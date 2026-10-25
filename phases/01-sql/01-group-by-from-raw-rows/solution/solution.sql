-- Lesson 01: GROUP BY from raw rows. Worked answer.
-- Table: orders(order_id, customer_id, city, order_date, amount, status)

-- query: status_counts
SELECT status, COUNT(*) AS orders
FROM orders
GROUP BY status
ORDER BY status;

-- query: city_totals
SELECT
  city,
  COUNT(*) AS orders,
  ROUND(SUM(amount), 2) AS revenue,
  ROUND(AVG(amount), 2) AS avg_order
FROM orders
WHERE status = 'completed'
GROUP BY city
ORDER BY city;

-- query: busy_cities
SELECT
  city,
  COUNT(*) AS orders,
  ROUND(SUM(amount), 2) AS revenue
FROM orders
WHERE status = 'completed'
GROUP BY city
HAVING COUNT(*) >= 70
ORDER BY revenue DESC;
