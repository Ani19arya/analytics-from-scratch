-- Lesson 10: slowly changing dimensions. Your turn.
-- Tables: customer_changes(change_id, customer_id, region, changed_on 'YYYY-MM-DD')
--           the CRM's change log. change_id is the order rows were loaded, not the
--           order changes happened. Look at the data before you trust it.
--         orders(order_id, customer_id, order_date 'YYYY-MM-DD', amount)
--         dim_customer(customer_key, customer_id, region, valid_from, valid_to, is_current)
--           a correct Type 2 dimension, loaded by the test before the last three
--           queries run, so each query is checked on its own.
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py

-- query: scd_type1
-- TODO: one row per customer with the region on their latest record.
-- Columns: customer_id, region. Order by customer_id.


-- query: scd_type2
-- TODO: one row per version of each customer: a new version only when the region changes.
-- valid_from is inclusive, valid_to is the next version's valid_from, and the
-- current version has valid_to '9999-12-31' and is_current 1 (else 0).
-- customer_key numbers the rows 1, 2, 3, ... in the output order.
-- Columns: customer_key, customer_id, region, valid_from, valid_to, is_current.
-- Order by customer_id, valid_from.


-- query: orders_with_region
-- TODO: every order, with the region the customer was in on the order date and
-- the region they are in now (from dim_customer). 'Unknown' when there is no match.
-- Columns: order_id, customer_id, order_date, amount, region_at_order, region_now.
-- Order by order_id.


-- query: revenue_by_region_as_ordered
-- TODO: orders and revenue by the region the customer was in when they ordered.
-- Columns: region, orders, revenue (rounded to 2). Order by region.


-- query: revenue_by_region_current
-- TODO: the same, by the region the customer is in today.
-- Columns: region, orders, revenue (rounded to 2). Order by region.
