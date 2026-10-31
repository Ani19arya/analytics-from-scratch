-- Lesson 08-01 solution: warehouse layers.
-- Each "-- model:" block is one SELECT. warehouse.py builds them in this order,
-- as tables, from the raw layer. Nothing here edits raw.

-- model: stg_customers
-- Staging: one row per customer, the latest load wins, city cleaned.
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
-- Staging: one row per order, the latest load wins, every column typed.
WITH ranked AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY load_id DESC) AS rn
  FROM raw_orders
)
SELECT
  order_id,
  customer_id,
  CASE WHEN ordered_at LIKE '__/__/____%'
       THEN SUBSTR(ordered_at, 7, 4) || '-' || SUBSTR(ordered_at, 4, 2) || '-' || SUBSTR(ordered_at, 1, 2)
       ELSE SUBSTR(ordered_at, 1, 10) END AS order_date,
  LOWER(TRIM(status)) AS status,
  CAST(NULLIF(REPLACE(TRIM(amount), ',', ''), '') AS REAL) AS amount,
  CAST(discount AS REAL) AS discount
FROM ranked
WHERE rn = 1;

-- model: fct_orders
-- Mart (fact table): one row per order, with the city, and revenue defined ONCE.
SELECT
  o.order_id,
  o.customer_id,
  COALESCE(c.city, 'Unknown') AS city,
  o.order_date,
  SUBSTR(o.order_date, 1, 7) AS order_month,
  o.status,
  o.amount,
  o.discount,
  CASE WHEN o.status = 'delivered' THEN o.amount - o.discount END AS revenue
FROM stg_orders AS o
LEFT JOIN stg_customers AS c ON c.customer_id = o.customer_id;

-- model: mart_city_month
SELECT
  city,
  order_month,
  SUM(status = 'delivered') AS delivered_orders,
  ROUND(COALESCE(SUM(revenue), 0), 2) AS revenue,
  SUM(status = 'delivered' AND amount IS NULL) AS missing_amount
FROM fct_orders
GROUP BY city, order_month;

-- model: mart_customers
SELECT
  customer_id,
  MAX(city) AS city,
  MIN(order_month) AS first_order_month,
  COUNT(*) AS orders,
  SUM(status = 'delivered') AS delivered_orders,
  ROUND(COALESCE(SUM(revenue), 0), 2) AS revenue
FROM fct_orders
GROUP BY customer_id;
