-- Lesson 00-04: your first SQL query. Your turn.
-- Table:
--   orders(order_id, order_date, city, status, amount)
--   order_date is text in the form YYYY-MM-DD. status is 'delivered' or 'cancelled'.
-- Write one query under each "-- query:" marker. Keep the markers.
-- Try any query first with, from the repo root:
--   python3 tools/query.py phases/00-start-here/04-your-first-sql-query "SELECT ..."
-- Then run, from this folder: python3 test_lesson.py

-- query: first_look
-- TODO: every column of the 5 orders with the smallest order_id.
-- Hint: SELECT * means every column. Sort with ORDER BY, keep 5 rows with LIMIT.


-- query: top_ten_last_week
-- TODO: the 10 biggest DELIVERED orders of last week (Monday 19 to Sunday 25 October 2026,
-- both days included). Columns, in this order: order_id, order_date, city, amount.
-- Biggest amount first. When two amounts are equal, the smaller order_id comes first.


-- query: big_orders_pune_nagpur
-- TODO: delivered orders of last week with an amount of 1000 or more,
-- from Pune or Nagpur only. Columns: order_id, city, amount. Order by order_id.
-- Careful: AND is done before OR. Use brackets ( ) or IN (...).

