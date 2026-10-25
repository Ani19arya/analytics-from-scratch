-- Lesson 04: cohort retention. Worked answer.
-- Tables:
--   users(user_id, signup_date)    dates are text 'YYYY-MM-DD'
--   events(user_id, event_date)

-- query: cohort_sizes
SELECT strftime('%Y-%m', signup_date) AS cohort_month, COUNT(*) AS users
FROM users
GROUP BY cohort_month
ORDER BY cohort_month;

-- query: retention
WITH cohorts AS (
  SELECT user_id, strftime('%Y-%m', signup_date) AS cohort_month, signup_date
  FROM users
),
activity AS (
  SELECT DISTINCT
    c.user_id,
    c.cohort_month,
    (CAST(strftime('%Y', e.event_date) AS INTEGER) - CAST(strftime('%Y', c.signup_date) AS INTEGER)) * 12
      + CAST(strftime('%m', e.event_date) AS INTEGER) - CAST(strftime('%m', c.signup_date) AS INTEGER)
      AS month_number
  FROM cohorts c
  JOIN events e ON e.user_id = c.user_id
),
sizes AS (
  SELECT cohort_month, COUNT(*) AS cohort_size
  FROM cohorts
  GROUP BY cohort_month
)
SELECT
  a.cohort_month,
  a.month_number,
  COUNT(DISTINCT a.user_id) AS active_users,
  s.cohort_size,
  ROUND(100.0 * COUNT(DISTINCT a.user_id) / s.cohort_size, 1) AS retention_pct
FROM activity a
JOIN sizes s ON s.cohort_month = a.cohort_month
GROUP BY a.cohort_month, a.month_number, s.cohort_size
ORDER BY a.cohort_month, a.month_number;
