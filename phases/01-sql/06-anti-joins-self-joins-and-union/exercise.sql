-- Lesson 06: anti-joins, self-joins and UNION. Your turn.
-- Tables:
--   customers(customer_id, name, city, referred_by)   referred_by is a customer_id or NULL
--   web_orders(order_id, customer_id, order_date, amount)   customer_id is NULL for a guest checkout
--   app_orders(order_id, customer_id, order_date, amount)
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py
-- Try a query on its own first: python3 ../query.py "SELECT * FROM web_orders LIMIT 5"
--
-- Orders come from two systems: always look at BOTH order tables.

-- query: monthly_orders
-- TODO: orders and revenue per month, from web_orders and app_orders together.
-- Columns: month ('YYYY-MM'), orders, revenue (rounded to 2 decimals). Order by month.
-- Every row of both tables is a real order, guest orders included.


-- query: lapsed_customers
-- TODO: customers with at least one order in March 2026 and no order in April 2026,
-- counting orders from both tables.
-- Columns: customer_id, name, referrer_name. Order by customer_id.
-- referrer_name is the name of the customer in referred_by, or NULL if there is none.
-- Careful: guest orders have customer_id NULL.


-- query: march_april_summary
-- TODO: one row with five columns, counting customers (not guests, not orders):
--   march_customers  customers with an order in March
--   april_customers  customers with an order in April
--   both_months      customers with an order in both
--   march_only       customers with an order in March and none in April
--   either_month     customers with an order in March or April, each counted once
