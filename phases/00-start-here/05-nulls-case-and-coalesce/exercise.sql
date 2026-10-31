-- Lesson 00-05: NULLs, CASE and COALESCE. Your turn.
-- Table:
--   orders(order_id, order_date, city, status, amount, delivered_date, tip)
--   An empty cell in the CSV is NULL in the table.
--   status is 'delivered', 'cancelled' or 'in_transit'.
-- Write one query under each "-- query:" marker. Keep the markers.
-- Try any query first with, from the repo root:
--   python3 tools/query.py phases/00-start-here/05-nulls-case-and-coalesce "SELECT ..."
-- Then run, from this folder: python3 test_lesson.py

-- query: delivery_date_counts
-- TODO: one row, three columns:
--   total_orders = every row
--   with_date    = rows where delivered_date is filled in
--   without_date = rows where delivered_date is NULL
-- Hint: COUNT(*) counts rows, COUNT(column) counts only non-NULL values.


-- query: orders_without_delivery_date
-- TODO: order_id and status of every order with no delivered_date. Order by order_id.
-- Hint: = NULL never matches. Use IS NULL.


-- query: order_sizes
-- TODO: every order with order_id, amount and a column called size:
--   'unknown' if amount is NULL, 'small' under 300, 'medium' from 300 to under 800,
--   'large' from 800 up. Order by order_id.
-- Hint: CASE checks its WHEN lines from the top and stops at the first true one.


-- query: size_counts
-- TODO: one row with four columns, small, medium, large, unknown:
-- the number of orders in each size. Hint: SUM(CASE WHEN ... THEN 1 ELSE 0 END)


-- query: tip_summary
-- TODO: one row with three columns:
--   tips_recorded          = how many orders have a tip recorded (0 counts as recorded)
--   avg_tip_recorded       = the average tip over recorded tips only, rounded to 2 decimals
--   avg_tip_blank_as_zero  = the average if a blank tip is treated as 0, rounded to 2 decimals
-- Hint: AVG skips NULLs. COALESCE(tip, 0) turns NULL into 0.

