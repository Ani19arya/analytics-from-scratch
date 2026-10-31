-- Lesson 08-01: warehouse layers. Your turn.
-- Raw tables (never edit them, only read them):
--   raw_orders(load_id, order_id, customer_id, ordered_at, status, amount, discount)
--   raw_customers(load_id, customer_id, city, signup_date)
-- Each "-- model: <name>" block is ONE SELECT. warehouse.py builds the blocks
-- in this order as tables, so a model can read the raw tables and any model
-- above it. Keep the markers and the order.
-- Run from this folder: python3 test_lesson.py

-- model: stg_customers
-- Done for you, as the pattern for staging: latest load wins, clean one column.
WITH ranked AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY load_id DESC) AS rn
  FROM raw_customers
)
SELECT
  customer_id,
  CASE WHEN TRIM(city) = '' OR city IS NULL THEN NULL
       ELSE UPPER(SUBSTR(TRIM(city), 1, 1)) || LOWER(SUBSTR(TRIM(city), 2)) END AS city,
  signup_date
FROM ranked
WHERE rn = 1;

-- model: stg_orders
-- TODO: one row per order_id (the row with the highest load_id).
-- Columns: order_id, customer_id, order_date ('YYYY-MM-DD', from either
-- format of ordered_at), status (lower case, trimmed), amount (REAL, NULL when
-- empty, thousands commas removed), discount (REAL).


-- model: fct_orders
-- TODO: one row per order from stg_orders, with the customer's city
-- ('Unknown' when there is none) and order_month ('YYYY-MM').
-- This is the ONLY place revenue is defined: amount - discount for a
-- delivered order, NULL for everything else.
-- Columns: order_id, customer_id, city, order_date, order_month, status,
-- amount, discount, revenue.


-- model: mart_city_month
-- TODO: one row per city and order_month that has any order.
-- Columns: city, order_month, delivered_orders, revenue (rounded to 2,
-- 0 when nothing counts), missing_amount (delivered orders with no amount yet).


-- model: mart_customers
-- TODO: one row per customer who ordered.
-- Columns: customer_id, city, first_order_month, orders (all statuses),
-- delivered_orders, revenue (rounded to 2, 0 when nothing counts).

