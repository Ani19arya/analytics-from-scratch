-- Lesson 11: row-level security. Worked answer.
-- Tables: sales(order_id, order_date, city (NULL when not assigned yet), amount)
--         user_access(user_email, city ('*' means every city), active (1 or 0))
-- The first two queries take one parameter, :user, the login of the person viewing.

-- query: visible_sales
-- Deny by default: a row is shown only if an active mapping row for this user
-- grants its city, or grants '*'. No mapping, no rows.
-- EXISTS, not JOIN: a pair typed twice in user_access must not show a sale twice.
-- lower(trim(...)) on both sides: logins and hand-typed emails differ in case and spaces.
-- A NULL city never equals anything, so only '*' sees unassigned orders.
SELECT s.order_id, s.order_date, s.city, s.amount
FROM sales s
WHERE EXISTS (
  SELECT 1
  FROM user_access a
  WHERE lower(trim(a.user_email)) = lower(trim(:user))
    AND a.active = 1
    AND (a.city = '*' OR a.city = s.city)
)
ORDER BY s.order_id;

-- query: visible_revenue_by_city
-- The dashboard visual, on top of the same rule.
SELECT COALESCE(s.city, 'Unassigned') AS city, COUNT(*) AS orders, ROUND(SUM(s.amount), 2) AS revenue
FROM sales s
WHERE EXISTS (
  SELECT 1
  FROM user_access a
  WHERE lower(trim(a.user_email)) = lower(trim(:user))
    AND a.active = 1
    AND (a.city = '*' OR a.city = s.city)
)
GROUP BY 1
ORDER BY 1;

-- query: access_audit
-- One row per person in the mapping table (email cleaned), with what they can see.
-- A person who can see nothing gets 0 and 0.00, not a missing row.
WITH people AS (SELECT DISTINCT lower(trim(user_email)) AS user_email FROM user_access)
SELECT p.user_email,
  COUNT(s.order_id) AS orders_visible,
  ROUND(COALESCE(SUM(s.amount), 0), 2) AS revenue_visible
FROM people p
LEFT JOIN sales s
  ON EXISTS (
    SELECT 1
    FROM user_access a
    WHERE lower(trim(a.user_email)) = p.user_email
      AND a.active = 1
      AND (a.city = '*' OR a.city = s.city)
  )
GROUP BY p.user_email
ORDER BY p.user_email;

-- query: uncovered_sales
-- Sales no active city-level mapping covers: only '*' users can see them.
-- These are the gaps to fix in the mapping table.
SELECT COALESCE(s.city, 'Unassigned') AS city, COUNT(*) AS orders, ROUND(SUM(s.amount), 2) AS revenue
FROM sales s
WHERE NOT EXISTS (
  SELECT 1 FROM user_access a WHERE a.active = 1 AND a.city = s.city
)
GROUP BY 1
ORDER BY 1;
