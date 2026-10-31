-- Lesson 07: subqueries and CTEs. Your turn.
-- Tables:
--   customers(customer_id, name, city)
--   orders(order_id, customer_id, order_date, amount)   October 2026, whole rupees
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py
-- Try a query on its own first: python3 ../query.py "SELECT * FROM orders LIMIT 5"
--
-- "Spend" means a customer's total for October: the sum of their orders.
-- Only customers who placed at least one order have a spend.

-- query: customer_totals
-- TODO: one row per customer who placed at least one order.
-- Columns: customer_id, city, orders, total_spent. Order by customer_id.


-- query: city_averages
-- TODO: one row per city: how many customers ordered, and the average of
-- their totals (not the average order).
-- Columns: city, customers, avg_spend (rounded to 2 decimals). Order by city.
-- Hint: WITH totals AS (...your customer_totals query...) SELECT ... FROM totals


-- query: above_average
-- TODO: the customers whose total is MORE than the average total of their
-- own city. A customer exactly at the average is not above it.
-- Columns: customer_id, name, city, total_spent, city_avg (rounded to 2 decimals).
-- Order by city, then total_spent from highest to lowest, then customer_id.
-- Compare with the unrounded average; round only for display.
