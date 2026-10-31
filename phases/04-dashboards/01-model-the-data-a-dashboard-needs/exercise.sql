-- Lesson 01: model the data a dashboard needs. Your turn.
-- Raw table:
--   transactions(order_id, line_no, order_date, product, category, unit_price,
--                region, region_manager, quantity)
-- The test runs the first four queries as CREATE TABLE <name> AS <query>, in
-- this order, so later queries can join to the tables built by earlier ones.
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py

-- query: dim_date
-- TODO: one row per calendar day from the first order_date to the last,
-- including days with no sales.
-- Columns: date_key (integer YYYYMMDD), date ('YYYY-MM-DD'), year, quarter (1 to 4),
-- month (1 to 12), year_month ('YYYY-MM'), weekday_num (0 = Sunday to 6 = Saturday),
-- weekday ('Sun', 'Mon', ... 'Sat').


-- query: dim_product
-- TODO: one row per product. Columns: product_key (integer, unique), product, category.


-- query: dim_region
-- TODO: one row per region. Columns: region_key (integer, unique), region, region_manager.


-- query: fact_sales
-- TODO: one row per order line (the grain of the raw table), keys and numbers only.
-- Columns: order_id, line_no, date_key, product_key, region_key, quantity,
-- revenue (quantity * unit_price, rounded to 2 decimals).


-- query: revenue_by_category_month
-- TODO: the first dashboard visual, built from the star schema (not from transactions).
-- Columns: year_month, category, revenue (rounded to 2 decimals).
-- Order by year_month, category.


-- query: orders_by_region
-- TODO: the orders card, by region, from the star schema.
-- Columns: region, orders (each order counted once), order_lines, revenue (rounded to 2).
-- Order by region.


-- query: revenue_by_weekday
-- TODO: revenue by day of the week, from the star schema, with Sunday included.
-- Columns: weekday_num, weekday, days (calendar days of that weekday),
-- revenue (rounded to 2, 0 when there were no sales). Order by weekday_num.

