-- Lesson 10: slowly changing dimensions. Worked answer.
-- Tables: customer_changes(change_id, customer_id, region, changed_on 'YYYY-MM-DD')
--         orders(order_id, customer_id, order_date 'YYYY-MM-DD', amount)
--         dim_customer(customer_key, customer_id, region, valid_from, valid_to, is_current)
--           the Type 2 dimension, loaded by the test before the last three queries run.

-- query: scd_type1
-- Type 1 keeps one row per customer and overwrites it: the latest save wins.
-- "Latest" is by changed_on, then change_id for two saves on the same day.
-- change_id alone is wrong: a move entered late has a high change_id and an old date.
SELECT customer_id, region
FROM (
  SELECT customer_id, region,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY changed_on DESC, change_id DESC) AS rn
  FROM customer_changes
) ranked
WHERE rn = 1
ORDER BY customer_id;

-- query: scd_type2
-- Type 2 keeps every version with the dates it was true.
-- 1. One save per customer and day: a same-day correction replaces the typo.
-- 2. Keep a save only if the region changed (a new street is not a new version).
-- 3. valid_to is the next version's valid_from (exclusive); the current one gets 9999-12-31.
WITH per_day AS (
  SELECT customer_id, region, changed_on,
    ROW_NUMBER() OVER (PARTITION BY customer_id, changed_on ORDER BY change_id DESC) AS rn
  FROM customer_changes
),
saves AS (
  SELECT customer_id, region, changed_on,
    LAG(region) OVER (PARTITION BY customer_id ORDER BY changed_on) AS prev_region
  FROM per_day
  WHERE rn = 1
),
versions AS (
  SELECT customer_id, region, changed_on AS valid_from,
    LEAD(changed_on) OVER (PARTITION BY customer_id ORDER BY changed_on) AS next_from
  FROM saves
  WHERE prev_region IS NULL OR prev_region <> region
)
SELECT ROW_NUMBER() OVER (ORDER BY customer_id, valid_from) AS customer_key,
  customer_id, region, valid_from,
  COALESCE(next_from, '9999-12-31') AS valid_to,
  CASE WHEN next_from IS NULL THEN 1 ELSE 0 END AS is_current
FROM versions
ORDER BY customer_id, valid_from;

-- query: orders_with_region
-- The point-in-time join: the version whose window holds the order date.
-- valid_from <= order_date < valid_to, so an order on the day of a move goes to the new region.
-- An order with no matching version (before the log started) is 'Unknown', never dropped.
SELECT o.order_id, o.customer_id, o.order_date, o.amount,
  COALESCE(at_order.region, 'Unknown') AS region_at_order,
  COALESCE(today.region, 'Unknown') AS region_now
FROM orders o
LEFT JOIN dim_customer at_order
  ON at_order.customer_id = o.customer_id
 AND o.order_date >= at_order.valid_from
 AND o.order_date < at_order.valid_to
LEFT JOIN dim_customer today
  ON today.customer_id = o.customer_id
 AND today.is_current = 1
ORDER BY o.order_id;

-- query: revenue_by_region_as_ordered
-- Each order counts in the region the customer was in when they ordered.
SELECT COALESCE(d.region, 'Unknown') AS region, COUNT(*) AS orders, ROUND(SUM(o.amount), 2) AS revenue
FROM orders o
LEFT JOIN dim_customer d
  ON d.customer_id = o.customer_id
 AND o.order_date >= d.valid_from
 AND o.order_date < d.valid_to
GROUP BY 1
ORDER BY 1;

-- query: revenue_by_region_current
-- What a Type 1 dimension gives: every order follows the customer to their region today.
SELECT COALESCE(d.region, 'Unknown') AS region, COUNT(*) AS orders, ROUND(SUM(o.amount), 2) AS revenue
FROM orders o
LEFT JOIN dim_customer d
  ON d.customer_id = o.customer_id
 AND d.is_current = 1
GROUP BY 1
ORDER BY 1;
