-- Lesson 14: SQL dialects for work and interviews. Your turn.
-- Tables:
--   customers(customer_id, city, signed_up_on)
--   orders(order_id, customer_id, ordered_at, amount, status, promo_code)
--     ordered_at is text 'YYYY-MM-DD HH:MM:SS'; promo_code is NULL when no code was used
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py
--
-- Write every query so it gives the same answer in any database: do not rely
-- on a default that differs between SQLite, Postgres, BigQuery and Snowflake.
-- The test also runs your queries with LIKE made case-sensitive, as it is in
-- Postgres, BigQuery and Snowflake.
-- Completed orders only, in every query.

-- query: monthly_revenue
-- TODO: month_start ('YYYY-MM-01'), orders, revenue. Order by month_start.


-- query: weekly_orders
-- TODO: week_start (the Monday of the week, 'YYYY-MM-DD'), orders. Order by week_start.


-- query: city_aov
-- TODO: city, orders, revenue, avg_order_value (2 decimals), fest_share (4 decimals):
-- the share of orders whose promo code starts with "fest" in any mix of capitals.
-- Order by city.


-- query: latest_order
-- TODO: customer_id, order_id, ordered_at, amount of each customer's latest order.
-- Two orders in the same second: the larger order_id is the later one. Order by customer_id.


-- query: second_order_gap
-- TODO: customer_id, first_order_date ('YYYY-MM-DD'), days_to_second (whole days
-- between the dates of the first and second orders; NULL if there is no second).
-- First and second are by ordered_at, then order_id.
-- Order by days_to_second, smallest first, customers with no second order last, then customer_id.
