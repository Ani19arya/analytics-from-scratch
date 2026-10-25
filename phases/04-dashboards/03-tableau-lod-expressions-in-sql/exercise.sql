-- Lesson 03: Tableau LOD expressions in SQL. Your turn.
-- Table: orders(order_id, customer_id, region, order_date 'YYYY-MM-DD', amount)
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py

-- query: customer_first_month
-- TODO: FIXED. Each customer's first order month ('YYYY-MM').
-- Columns: customer_id, first_order_month. Order by customer_id.


-- query: new_customers_by_month
-- TODO: how many customers made their FIRST order in each month.
-- Columns: first_order_month, new_customers. Order by first_order_month.


-- query: avg_customer_sales_by_region
-- TODO: INCLUDE. In each region, the average of each customer's total sales
-- (not the average order).
-- Columns: region, customers, avg_customer_sales (rounded to 2). Order by region.


-- query: region_month_share
-- TODO: EXCLUDE. One row per region and month with sales, next to the region's
-- sales across all months, and the month's share of it.
-- Columns: region, year_month, sales, region_sales (both rounded to 2),
-- pct_of_region (rounded to 4). Order by region, year_month.


-- query: customer_share_of_region
-- TODO: FIXED at region in a view by customer. Each customer's sales, their
-- region's total, and the customer's share of it.
-- Columns: customer_id, region, customer_sales, region_sales (both rounded to 2),
-- share_of_region (rounded to 4). Order by region, customer_sales DESC, customer_id.

