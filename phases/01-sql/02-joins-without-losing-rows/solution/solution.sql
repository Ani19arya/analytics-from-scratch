-- Lesson 02: joins without losing rows. Worked answer.
-- Tables:
--   customers(customer_id, signup_date)
--   orders(order_id, customer_id, amount)
--   customer_addresses(customer_id, city, is_primary)

-- query: row_counts
SELECT
  (SELECT COUNT(*) FROM customers) AS customers,
  (SELECT COUNT(*) FROM orders) AS orders,
  (SELECT COUNT(*) FROM customers c JOIN orders o ON o.customer_id = c.customer_id) AS inner_rows,
  (SELECT COUNT(*) FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id) AS left_rows;

-- query: customer_totals
-- COALESCE returns its first non-NULL argument, so a customer with no orders shows 0, not NULL.
SELECT
  c.customer_id,
  COUNT(o.order_id) AS order_count,
  ROUND(COALESCE(SUM(o.amount), 0), 2) AS total_spent
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id
ORDER BY c.customer_id;

-- query: customers_without_orders
-- NOT EXISTS is safe when orders.customer_id holds a NULL. NOT IN is not.
SELECT c.customer_id
FROM customers c
WHERE NOT EXISTS (
  SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id
)
ORDER BY c.customer_id;

-- query: revenue_by_city
-- LEFT JOIN keeps orders whose customer has no primary address (city NULL),
-- and is_primary = 1 in the ON clause gives at most one address per customer.
SELECT a.city, ROUND(SUM(o.amount), 2) AS revenue
FROM orders o
LEFT JOIN customer_addresses a
  ON a.customer_id = o.customer_id
 AND a.is_primary = 1
GROUP BY a.city
ORDER BY a.city;
