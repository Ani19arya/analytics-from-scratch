-- Lesson 00-04: your first SQL query. Worked answer.
-- Table:
--   orders(order_id, order_date, city, status, amount)

-- query: first_look
SELECT *
FROM orders
ORDER BY order_id
LIMIT 5;

-- query: top_ten_last_week
SELECT order_id, order_date, city, amount
FROM orders
WHERE status = 'delivered'
  AND order_date >= '2026-10-19'
  AND order_date <= '2026-10-25'
ORDER BY amount DESC, order_id
LIMIT 10;

-- query: big_orders_pune_nagpur
SELECT order_id, city, amount
FROM orders
WHERE status = 'delivered'
  AND order_date >= '2026-10-19'
  AND order_date <= '2026-10-25'
  AND amount >= 1000
  AND (city = 'Pune' OR city = 'Nagpur')
ORDER BY order_id;
