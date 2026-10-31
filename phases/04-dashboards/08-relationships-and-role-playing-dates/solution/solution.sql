-- Lesson 08: relationships, role-playing dates and many-to-many. Worked answer.
-- Tables: dim_date(date, year_month), orders(order_id, order_date, ship_date, amount),
--         campaigns(campaign_id, campaign_name), order_campaign(order_id, campaign_id)

-- query: revenue_by_order_month
-- The active relationship: orders[order_date] -> dim_date[date].
SELECT d.year_month, COUNT(*) AS orders, ROUND(SUM(o.amount), 2) AS revenue
FROM orders o
JOIN dim_date d ON d.date = o.order_date
GROUP BY d.year_month
ORDER BY d.year_month;

-- query: revenue_by_ship_month
-- USERELATIONSHIP(orders[ship_date], dim_date[date]): the same date table, the other key.
-- A LEFT JOIN keeps unshipped orders; they land on a NULL month, like Power BI's (Blank) row.
-- ORDER BY puts NULL first in SQLite; the CASE moves it to the end.
SELECT d.year_month, COUNT(*) AS orders, ROUND(SUM(o.amount), 2) AS revenue
FROM orders o
LEFT JOIN dim_date d ON d.date = o.ship_date
GROUP BY d.year_month
ORDER BY CASE WHEN d.year_month IS NULL THEN 1 ELSE 0 END, d.year_month;

-- query: revenue_by_campaign
-- Through the bridge. DISTINCT first: the export repeats a few (order, campaign) pairs.
WITH pairs AS (SELECT DISTINCT order_id, campaign_id FROM order_campaign)
SELECT c.campaign_name, COUNT(*) AS orders, ROUND(SUM(o.amount), 2) AS revenue
FROM pairs p
JOIN campaigns c ON c.campaign_id = p.campaign_id
JOIN orders o ON o.order_id = p.order_id
GROUP BY c.campaign_name
ORDER BY c.campaign_name;

-- query: campaign_totals
-- The rows of revenue_by_campaign do not add up to anything real: an order touched by
-- three campaigns is in three rows. The true total counts each order once.
WITH pairs AS (SELECT DISTINCT order_id, campaign_id FROM order_campaign),
by_campaign AS (
  SELECT SUM(o.amount) AS revenue FROM pairs p JOIN orders o ON o.order_id = p.order_id
)
SELECT
  ROUND(COALESCE((SELECT revenue FROM by_campaign), 0), 2) AS sum_of_campaign_rows,
  ROUND(COALESCE(SUM(CASE WHEN o.order_id IN (SELECT order_id FROM pairs) THEN o.amount END), 0), 2)
    AS revenue_with_a_campaign,
  ROUND(COALESCE(SUM(CASE WHEN o.order_id NOT IN (SELECT order_id FROM pairs) THEN o.amount END), 0), 2)
    AS revenue_without_a_campaign,
  ROUND(COALESCE(SUM(o.amount), 0), 2) AS total_revenue
FROM orders o;

-- query: revenue_by_campaign_allocated
-- Split each order equally across its distinct campaigns, so the rows add up to
-- revenue_with_a_campaign. One rule among several (first touch, last touch, weights).
WITH pairs AS (SELECT DISTINCT order_id, campaign_id FROM order_campaign),
weights AS (SELECT order_id, 1.0 / COUNT(*) AS weight FROM pairs GROUP BY order_id)
SELECT c.campaign_name, ROUND(SUM(o.amount * w.weight), 2) AS allocated_revenue
FROM pairs p
JOIN weights w ON w.order_id = p.order_id
JOIN campaigns c ON c.campaign_id = p.campaign_id
JOIN orders o ON o.order_id = p.order_id
GROUP BY c.campaign_name
ORDER BY c.campaign_name;
