-- Lesson 02: joins without losing rows. Your turn.
-- Tables:
--   customers(customer_id, signup_date)
--   orders(order_id, customer_id, amount)
--   customer_addresses(customer_id, city, is_primary)
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py
-- Try a query on its own first: python3 ../query.py "SELECT * FROM orders LIMIT 5"

-- query: row_counts
-- TODO: one row with four columns:
--   customers   = rows in customers
--   orders      = rows in orders
--   inner_rows  = rows from customers INNER JOIN orders on customer_id
--   left_rows   = rows from customers LEFT JOIN orders on customer_id


-- query: customer_totals
-- TODO: every customer exactly once, including customers with no orders.
-- Columns: customer_id, order_count, total_spent.
-- A customer with no orders has order_count 0 and total_spent 0.
-- An order with no amount still counts in order_count.
-- Round total_spent to 2 decimals. Order by customer_id.


-- query: customers_without_orders
-- TODO: customer_id of every customer who never ordered. Order by customer_id.
-- Careful: an order can have customer_id NULL (a guest checkout).


-- query: revenue_by_city
-- TODO: order revenue by the city of the customer's PRIMARY address.
-- Columns: city, revenue (rounded to 2 decimals). Order by city.
-- The revenue column must add up to the total of the orders table, so orders
-- whose customer has no primary address go in one row with city NULL.


