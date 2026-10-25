-- Lesson 02: DAX measures from scratch. Your turn.
-- Table: sales(order_date 'YYYY-MM-DD', category, channel, amount)
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py

-- query: sales_by_category
-- TODO: one row per category.
-- total_sales   = SUM(amount) for the category, rounded to 2 decimals
-- online_sales  = the same, but only channel 'Online', rounded to 2 decimals
-- share_of_all  = the category's sales / sales of ALL categories, rounded to 4 decimals
-- Columns: category, total_sales, online_sales, share_of_all. Order by category.


-- query: sales_ytd
-- TODO: one row per calendar month from the first month in the data to the last,
-- including months with no sales (sales = 0 for those).
-- ytd_sales = running total of sales that restarts every January.
-- Columns: year_month ('YYYY-MM'), sales, ytd_sales (both rounded to 2). Order by year_month.


-- query: sales_vs_last_year
-- TODO: one row for each month of 2026 that has sales.
-- sales_ly   = sales in the same calendar month one year earlier (0 if none), rounded to 2
-- growth_pct = (sales - sales_ly) * 100 / sales_ly rounded to 1, NULL when sales_ly is 0
-- Columns: year_month, sales, sales_ly, growth_pct. Order by year_month.

