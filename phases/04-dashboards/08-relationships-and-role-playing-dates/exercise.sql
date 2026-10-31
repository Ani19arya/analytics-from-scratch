-- Lesson 08: relationships, role-playing dates and many-to-many. Your turn.
-- Tables: dim_date(date 'YYYY-MM-DD', year_month 'YYYY-MM')
--         orders(order_id, order_date, ship_date (NULL if not shipped), amount)
--         campaigns(campaign_id, campaign_name)
--         order_campaign(order_id, campaign_id)   the bridge; the export repeats a few pairs
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py

-- query: revenue_by_order_month
-- TODO: revenue by ORDER month through dim_date.
-- Columns: year_month, orders, revenue (rounded to 2). Order by year_month.


-- query: revenue_by_ship_month
-- TODO: the same visual by SHIP month, through the same dim_date.
-- Every order must be counted once: unshipped orders go on one row with year_month NULL, last.
-- Columns: year_month, orders, revenue (rounded to 2).


-- query: revenue_by_campaign
-- TODO: one row per campaign that touched at least one order.
-- Columns: campaign_name, orders, revenue (rounded to 2). Order by campaign_name.


-- query: campaign_totals
-- TODO: one row. sum_of_campaign_rows (what you get by adding up revenue_by_campaign),
-- revenue_with_a_campaign (each such order once), revenue_without_a_campaign, total_revenue.
-- All rounded to 2, and 0 (not NULL) when there is nothing to add.


-- query: revenue_by_campaign_allocated
-- TODO: split each order's amount equally across its campaigns, so the rows add up to
-- revenue_with_a_campaign. Columns: campaign_name, allocated_revenue (rounded to 2). Order by campaign_name.
