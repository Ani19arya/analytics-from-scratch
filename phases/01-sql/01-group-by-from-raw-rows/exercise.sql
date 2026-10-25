-- Lesson 01: GROUP BY from raw rows. Your turn.
-- Table: orders(order_id, customer_id, city, order_date, amount, status)
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py

-- query: status_counts
-- TODO: one row per status with the number of orders.
-- Columns: status, orders. Order by status.


-- query: city_totals
-- TODO: completed orders only. One row per city.
-- Columns: city, orders, revenue, avg_order.
-- Round revenue and avg_order to 2 decimals. Order by city.


-- query: busy_cities
-- TODO: completed orders only. Keep cities with at least 70 completed orders.
-- Columns: city, orders, revenue (rounded to 2 decimals).
-- Order by revenue, highest first.

