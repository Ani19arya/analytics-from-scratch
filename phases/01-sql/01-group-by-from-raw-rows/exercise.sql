-- Lesson 01: GROUP BY from raw rows. Your turn.
-- Table: orders(order_id, customer_id, city, order_date, amount, status)
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py
-- Try a query on its own first: python3 ../query.py "SELECT * FROM orders LIMIT 5"

-- query: status_counts
-- TODO: one row per status with the number of orders.
-- Columns: status, orders. Order by status.


-- query: city_totals
-- TODO: completed orders only. One row per city.
-- Columns: city, orders, revenue, avg_order.
-- orders counts every completed order. revenue is the total amount.
-- avg_order is the average amount. An order with no amount (NULL) counts in
-- orders but not in the average.
-- Round revenue and avg_order to 2 decimals. Order by city.


-- query: busy_cities
-- TODO: completed orders only. Keep cities with at least 70 completed orders.
-- Columns: city, orders, revenue (rounded to 2 decimals).
-- Order by revenue, highest first. If two cities tie on revenue, order them by city.


