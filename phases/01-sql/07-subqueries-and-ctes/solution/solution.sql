-- Lesson 07: subqueries and CTEs. Worked answer.
-- Tables:
--   customers(customer_id, name, city)
--   orders(order_id, customer_id, order_date, amount)   October 2026, whole rupees
--
-- The city average is the average of CUSTOMER totals: first one row per
-- customer, then the average of those rows per city. Customers with no
-- October order are not in the average (they did not spend in October).

-- query: customer_totals
SELECT c.customer_id, c.city, COUNT(*) AS orders, SUM(o.amount) AS total_spent
FROM customers c
JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.city
ORDER BY c.customer_id;

-- query: city_averages
WITH totals AS (
  SELECT c.customer_id, c.city, SUM(o.amount) AS total_spent
  FROM customers c
  JOIN orders o ON o.customer_id = c.customer_id
  GROUP BY c.customer_id, c.city
)
SELECT city, COUNT(*) AS customers, ROUND(AVG(total_spent), 2) AS avg_spend
FROM totals
GROUP BY city
ORDER BY city;

-- query: above_average
WITH totals AS (
  -- step 1: one row per customer who ordered
  SELECT c.customer_id, c.name, c.city, SUM(o.amount) AS total_spent
  FROM customers c
  JOIN orders o ON o.customer_id = c.customer_id
  GROUP BY c.customer_id, c.name, c.city
),
city_avg AS (
  -- step 2: one row per city, the average of the customer totals
  SELECT city, AVG(total_spent) AS avg_spend
  FROM totals
  GROUP BY city
)
-- step 3: compare each customer with their own city, unrounded, strictly greater
SELECT t.customer_id, t.name, t.city, t.total_spent, ROUND(a.avg_spend, 2) AS city_avg
FROM totals t
JOIN city_avg a ON a.city = t.city
WHERE t.total_spent > a.avg_spend
ORDER BY t.city, t.total_spent DESC, t.customer_id;
