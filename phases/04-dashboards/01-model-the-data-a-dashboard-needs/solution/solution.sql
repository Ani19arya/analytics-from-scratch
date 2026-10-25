-- Lesson 01: model the data a dashboard needs. Worked answer.
-- Raw table:
--   transactions(order_id, line_no, order_date, product, category, unit_price,
--                region, region_manager, quantity)
-- The test runs each query as CREATE TABLE <name> AS <query>, in this order,
-- so later queries can join to the tables built by earlier ones.

-- query: dim_date
WITH RECURSIVE days(date) AS (
  SELECT MIN(order_date) FROM transactions
  UNION ALL
  SELECT date(date, '+1 day') FROM days
  WHERE date < (SELECT MAX(order_date) FROM transactions)
)
SELECT
  CAST(strftime('%Y%m%d', date) AS INTEGER) AS date_key,
  date,
  CAST(strftime('%Y', date) AS INTEGER) AS year,
  (CAST(strftime('%m', date) AS INTEGER) + 2) / 3 AS quarter,
  CAST(strftime('%m', date) AS INTEGER) AS month,
  strftime('%Y-%m', date) AS year_month
FROM days;

-- query: dim_product
SELECT
  ROW_NUMBER() OVER (ORDER BY product) AS product_key,
  product,
  category
FROM (SELECT DISTINCT product, category FROM transactions);

-- query: dim_region
SELECT
  ROW_NUMBER() OVER (ORDER BY region) AS region_key,
  region,
  region_manager
FROM (SELECT DISTINCT region, region_manager FROM transactions);

-- query: fact_sales
SELECT
  t.order_id,
  t.line_no,
  d.date_key,
  p.product_key,
  r.region_key,
  t.quantity,
  ROUND(t.quantity * t.unit_price, 2) AS revenue
FROM transactions t
JOIN dim_date d ON d.date = t.order_date
JOIN dim_product p ON p.product = t.product
JOIN dim_region r ON r.region = t.region;

-- query: revenue_by_category_month
SELECT
  d.year_month,
  p.category,
  ROUND(SUM(f.revenue), 2) AS revenue
FROM fact_sales f
JOIN dim_date d ON d.date_key = f.date_key
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY d.year_month, p.category
ORDER BY d.year_month, p.category;
