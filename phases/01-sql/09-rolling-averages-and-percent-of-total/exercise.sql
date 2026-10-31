-- Lesson 09: rolling averages and percent of total. Your turn.
-- Tables:
--   orders(order_id, order_date, region, amount)   no row at all on a day with no orders
--   report_period(start_date, end_date)            one row: the days the report covers
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py
-- Try a query on its own first: python3 ../query.py "SELECT * FROM orders LIMIT 5"
--
-- Diana's definitions:
--   A day with no orders counts as a day with 0 orders.
--   The 7-day moving average on a day is the average of that day and the 6
--   calendar days before it. Days before the report period do not exist for
--   this report, so the first 6 days have no average (NULL).
--   An order with no region counts as region 'Unassigned'.

-- query: daily_orders
-- TODO: one row per day of the report period.
-- Columns: day, orders, revenue. Order by day.


-- query: moving_avg
-- TODO: one row per day of the report period.
-- Columns: day, orders, avg_7d (rounded to 2 decimals, NULL for the first 6 days).
-- Order by day.


-- query: region_share
-- TODO: revenue per region in the report period, and its share of the total.
-- Columns: region, revenue, share_pct (percent, rounded to 1 decimal; NULL if the
-- total is 0). Order by revenue from highest to lowest, then region.
