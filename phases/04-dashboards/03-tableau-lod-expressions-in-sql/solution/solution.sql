-- Lesson 03: Tableau LOD expressions in SQL. Worked answer.
-- Table: orders(order_id, customer_id, region, order_date 'YYYY-MM-DD', amount)

-- query: customer_first_month
-- {FIXED [Customer ID] : MIN([Order Date])}
SELECT customer_id, MIN(substr(order_date, 1, 7)) AS first_order_month
FROM orders
GROUP BY customer_id
ORDER BY customer_id;

-- query: new_customers_by_month
SELECT first_order_month, COUNT(*) AS new_customers
FROM (
  SELECT customer_id, MIN(substr(order_date, 1, 7)) AS first_order_month
  FROM orders
  GROUP BY customer_id
) firsts
GROUP BY first_order_month
ORDER BY first_order_month;

-- query: avg_customer_sales_by_region
-- AVG({INCLUDE [Customer ID] : SUM([Amount])}) in a view by region
SELECT region, COUNT(*) AS customers, ROUND(AVG(customer_sales), 2) AS avg_customer_sales
FROM (
  SELECT region, customer_id, SUM(amount) AS customer_sales
  FROM orders
  GROUP BY region, customer_id
) per_customer
GROUP BY region
ORDER BY region;

-- query: region_month_share
-- {EXCLUDE [Month] : SUM([Amount])} in a view by region and month
SELECT
  region,
  year_month,
  ROUND(sales, 2) AS sales,
  ROUND(SUM(sales) OVER (PARTITION BY region), 2) AS region_sales,
  ROUND(sales / SUM(sales) OVER (PARTITION BY region), 4) AS pct_of_region
FROM (
  SELECT region, substr(order_date, 1, 7) AS year_month, SUM(amount) AS sales
  FROM orders
  GROUP BY region, year_month
) monthly
ORDER BY region, year_month;

-- query: customer_share_of_region
-- SUM([Amount]) / {FIXED [Region] : SUM([Amount])} in a view by customer
SELECT
  customer_id,
  region,
  ROUND(customer_sales, 2) AS customer_sales,
  ROUND(SUM(customer_sales) OVER (PARTITION BY region), 2) AS region_sales,
  ROUND(customer_sales / SUM(customer_sales) OVER (PARTITION BY region), 4) AS share_of_region
FROM (
  SELECT customer_id, region, SUM(amount) AS customer_sales
  FROM orders
  GROUP BY customer_id, region
) per_customer
ORDER BY region, customer_sales DESC, customer_id;
