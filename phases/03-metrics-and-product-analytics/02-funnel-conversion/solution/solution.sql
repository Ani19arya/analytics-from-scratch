-- Lesson 02: funnel conversion. Worked answer.
-- Table: events(user_id, event_name, event_time)   event_time is text 'YYYY-MM-DD HH:MM:SS'
-- Steps in order: view_course, add_to_cart, begin_checkout, purchase
-- Comparing event_time as text gives time order only because the format is
-- ISO (biggest unit first, fixed width). In other databases use a timestamp column.

-- query: events_per_step
SELECT event_name, COUNT(*) AS events, COUNT(DISTINCT user_id) AS users
FROM events
GROUP BY event_name
ORDER BY CASE event_name
  WHEN 'view_course' THEN 1 WHEN 'add_to_cart' THEN 2
  WHEN 'begin_checkout' THEN 3 WHEN 'purchase' THEN 4 END;

-- query: funnel
WITH firsts AS (
  SELECT
    user_id,
    MIN(CASE WHEN event_name = 'view_course' THEN event_time END) AS t1,
    MIN(CASE WHEN event_name = 'add_to_cart' THEN event_time END) AS t2,
    MIN(CASE WHEN event_name = 'begin_checkout' THEN event_time END) AS t3,
    MIN(CASE WHEN event_name = 'purchase' THEN event_time END) AS t4
  FROM events
  GROUP BY user_id
),
reached AS (
  -- CASE WHEN ... THEN 1 ELSE 0 END works in every database. A comparison with
  -- NULL is not true, so a user missing a step gets 0.
  SELECT
    user_id,
    CASE WHEN t1 IS NOT NULL THEN 1 ELSE 0 END AS s1,
    CASE WHEN t1 IS NOT NULL AND t2 >= t1 THEN 1 ELSE 0 END AS s2,
    CASE WHEN t1 IS NOT NULL AND t2 >= t1 AND t3 >= t2 THEN 1 ELSE 0 END AS s3,
    CASE WHEN t1 IS NOT NULL AND t2 >= t1 AND t3 >= t2 AND t4 >= t3 THEN 1 ELSE 0 END AS s4
  FROM firsts
),
steps AS (
  -- UNION ALL stacks the four one-row results into one table, keeping every row.
  SELECT 1 AS step_number, 'view_course' AS step, SUM(s1) AS users FROM reached
  UNION ALL SELECT 2, 'add_to_cart', SUM(s2) FROM reached
  UNION ALL SELECT 3, 'begin_checkout', SUM(s3) FROM reached
  UNION ALL SELECT 4, 'purchase', SUM(s4) FROM reached
)
SELECT
  step_number,
  step,
  users,
  ROUND(100.0 * users / LAG(users, 1, users) OVER (ORDER BY step_number), 1) AS step_conversion_pct,
  ROUND(100.0 * users / FIRST_VALUE(users) OVER (ORDER BY step_number), 1) AS overall_conversion_pct
FROM steps
ORDER BY step_number;

-- query: biggest_drop
WITH firsts AS (
  SELECT
    user_id,
    MIN(CASE WHEN event_name = 'view_course' THEN event_time END) AS t1,
    MIN(CASE WHEN event_name = 'add_to_cart' THEN event_time END) AS t2,
    MIN(CASE WHEN event_name = 'begin_checkout' THEN event_time END) AS t3,
    MIN(CASE WHEN event_name = 'purchase' THEN event_time END) AS t4
  FROM events
  GROUP BY user_id
),
reached AS (
  SELECT
    CASE WHEN t1 IS NOT NULL THEN 1 ELSE 0 END AS s1,
    CASE WHEN t1 IS NOT NULL AND t2 >= t1 THEN 1 ELSE 0 END AS s2,
    CASE WHEN t1 IS NOT NULL AND t2 >= t1 AND t3 >= t2 THEN 1 ELSE 0 END AS s3,
    CASE WHEN t1 IS NOT NULL AND t2 >= t1 AND t3 >= t2 AND t4 >= t3 THEN 1 ELSE 0 END AS s4
  FROM firsts
),
steps AS (
  SELECT 1 AS step_number, 'view_course' AS step, SUM(s1) AS users FROM reached
  UNION ALL SELECT 2, 'add_to_cart', SUM(s2) FROM reached
  UNION ALL SELECT 3, 'begin_checkout', SUM(s3) FROM reached
  UNION ALL SELECT 4, 'purchase', SUM(s4) FROM reached
),
conv AS (
  SELECT
    step_number,
    LAG(step, 1) OVER (ORDER BY step_number) AS from_step,
    step AS to_step,
    LAG(users, 1) OVER (ORDER BY step_number) - users AS users_lost,
    ROUND(100.0 * users / LAG(users, 1) OVER (ORDER BY step_number), 1) AS step_conversion_pct
  FROM steps
)
SELECT from_step, to_step, users_lost, step_conversion_pct
FROM conv
WHERE from_step IS NOT NULL
ORDER BY step_conversion_pct ASC, step_number ASC
LIMIT 1;
