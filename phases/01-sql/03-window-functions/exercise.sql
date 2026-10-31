-- Lesson 03: window functions. Your turn.
-- Tables:
--   monthly_revenue(region, month, revenue)   month is text 'YYYY-MM'
--   rep_sales(rep, region, sales)
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py
-- Try a query on its own first: python3 ../query.py "SELECT * FROM rep_sales"

-- query: running_total
-- TODO: every row of monthly_revenue plus running_total, the cumulative
-- revenue of that region from its first month up to this month
-- (fiscal year to date: the data is one October to September year).
-- A month with no revenue figure (NULL) adds nothing.
-- Columns: region, month, revenue, running_total. Order by region, month.


-- query: rep_rank
-- TODO: within each region, rank reps by sales, highest first.
-- sales_rank uses RANK (ties share a rank).
-- row_num uses ROW_NUMBER, breaking ties by rep name ascending.
-- Columns: region, rep, sales, sales_rank, row_num. Order by region, row_num.


-- query: top_reps
-- TODO: every rep whose sales are the highest in their region (keep ties).
-- Columns: region, rep. Order by region, rep.


-- query: month_over_month
-- TODO: each region's revenue next to the previous month's revenue.
-- Columns: region, month, revenue, prev_revenue, change (revenue - prev_revenue).
-- The first month of each region has NULL for prev_revenue and change.
-- Order by region, month.


-- query: rep_cumulative
-- TODO: within each region, go down the reps from the highest sales to the
-- lowest (ties broken by rep name) and keep a running total of sales.
-- Each rep gets their own value: two tied reps must NOT get the same total.
-- Columns: region, rep, sales, cumulative_sales.
-- Order by region, sales (highest first), rep.


