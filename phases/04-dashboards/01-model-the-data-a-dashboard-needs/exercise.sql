-- Lesson 01: model the data a dashboard needs. Your turn.
-- Raw table:
--   transactions(order_id, line_no, order_date, product, category, unit_price,
--                region, region_manager, quantity)
-- The test runs each query as CREATE TABLE <name> AS <query>, in this order,
-- so later queries can join to the tables built by earlier ones.
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py

-- query: dim_date
-- TODO: one row per calendar day from the first order_date to the last,
-- including days with no sales.
-- Columns: date_key (integer YYYYMMDD), date ('YYYY-MM-DD'), year, quarter (1 to 4),
-- month (1 to 12), year_month ('YYYY-MM').


-- query: dim_product
-- TODO: one row per product. Columns: product_key (integer, unique), product, category.


-- query: dim_region
-- TODO: one row per region. Columns: region_key (integer, unique), region, region_manager.


-- query: fact_sales
-- TODO: one row per order line (the grain of the raw table).
-- Columns: order_id, line_no, date_key, product_key, region_key, quantity,
-- revenue (quantity * unit_price, rounded to 2 decimals).


-- query: revenue_by_category_month
-- TODO: the first dashboard visual, built from the star schema (not from transactions).
-- Columns: year_month, category, revenue (rounded to 2 decimals).
-- Order by year_month, category.

