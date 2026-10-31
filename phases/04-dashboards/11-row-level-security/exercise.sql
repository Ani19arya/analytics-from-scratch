-- Lesson 11: row-level security. Your turn.
-- Tables: sales(order_id, order_date, city (NULL when not assigned yet), amount)
--         user_access(user_email, city, active)
--           the security mapping table, typed by hand: one row per (user, city).
--           city '*' means every city. active is 0 for people who have left.
-- The first two queries take one parameter, :user, the login of the person viewing
-- (sqlite3 fills it in: con.execute(sql, {"user": "someone@example.com"})).
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py

-- query: visible_sales
-- TODO: the sales :user may see. Someone with no active mapping row sees nothing.
-- Columns: order_id, order_date, city, amount. Order by order_id.


-- query: visible_revenue_by_city
-- TODO: the dashboard visual for :user, on the same rule. A NULL city shows as 'Unassigned'.
-- Columns: city, orders, revenue (rounded to 2). Order by city.


-- query: access_audit
-- TODO: no parameter. One row per person in user_access (email lower case, no spaces)
-- with how many orders and how much revenue they can see.
-- Columns: user_email, orders_visible, revenue_visible (rounded to 2, 0 when none).
-- Order by user_email.


-- query: uncovered_sales
-- TODO: no parameter. Sales that no active city-level row covers, so only '*' users see them.
-- Columns: city ('Unassigned' for NULL), orders, revenue (rounded to 2). Order by city.
