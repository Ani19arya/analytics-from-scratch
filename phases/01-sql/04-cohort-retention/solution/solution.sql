-- Lesson 04: cohort retention. Worked answer.
-- Tables:
--   users(user_id, signup_date)    dates are text 'YYYY-MM-DD'
--   events(user_id, event_date)
--
-- A month index turns a date into one whole number of months:
--   year * 12 + month, so 2026-01 is 24313 and 2026-02 is 24314.
-- month_number = month index of the event - month index of the signup.

-- query: cohort_sizes
SELECT strftime('%Y-%m', signup_date) AS cohort_month, COUNT(*) AS users
FROM users
GROUP BY cohort_month
ORDER BY cohort_month;

-- query: retention
WITH cohorts AS (
  -- one row per user: their cohort and the month index of their signup
  SELECT
    user_id,
    strftime('%Y-%m', signup_date) AS cohort_month,
    CAST(strftime('%Y', signup_date) AS INTEGER) * 12 + CAST(strftime('%m', signup_date) AS INTEGER) AS cohort_index
  FROM users
),
sizes AS (
  -- the denominator: every user in the cohort, active or not
  SELECT cohort_month, cohort_index, COUNT(*) AS cohort_size
  FROM cohorts
  GROUP BY cohort_month, cohort_index
),
months AS (
  -- every calendar month that appears in the events, as a month index
  SELECT DISTINCT CAST(strftime('%Y', event_date) AS INTEGER) * 12 + CAST(strftime('%m', event_date) AS INTEGER) AS month_index
  FROM events
),
grid AS (
  -- every cohort x every month from its signup month to the end of the data,
  -- so a month where nobody came back is a row with 0, not a missing row
  SELECT s.cohort_month, s.cohort_size, m.month_index - s.cohort_index AS month_number
  FROM sizes s
  JOIN months m ON m.month_index >= s.cohort_index
),
activity AS (
  -- one row per user and month number they were active in (DISTINCT removes repeat events)
  SELECT DISTINCT
    c.user_id,
    c.cohort_month,
    CAST(strftime('%Y', e.event_date) AS INTEGER) * 12 + CAST(strftime('%m', e.event_date) AS INTEGER) - c.cohort_index AS month_number
  FROM cohorts c
  JOIN events e ON e.user_id = c.user_id
)
SELECT
  g.cohort_month,
  g.month_number,
  COUNT(a.user_id) AS active_users,
  g.cohort_size,
  ROUND(100.0 * COUNT(a.user_id) / g.cohort_size, 1) AS retention_pct
FROM grid g
LEFT JOIN activity a
  ON a.cohort_month = g.cohort_month
 AND a.month_number = g.month_number
GROUP BY g.cohort_month, g.month_number, g.cohort_size
ORDER BY g.cohort_month, g.month_number;
