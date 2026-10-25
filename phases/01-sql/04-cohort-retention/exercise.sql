-- Lesson 04: cohort retention. Your turn.
-- Tables:
--   users(user_id, signup_date)    dates are text 'YYYY-MM-DD'
--   events(user_id, event_date)
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py

-- query: cohort_sizes
-- TODO: number of users per signup month.
-- Columns: cohort_month ('YYYY-MM'), users. Order by cohort_month.
-- Hint: strftime('%Y-%m', signup_date)


-- query: retention
-- TODO: the retention table in long form. One row per cohort and month number
-- that has at least one active user.
-- month_number = months between the signup month and the event month
--   (0 = the signup month, 1 = the next calendar month, ...).
-- active_users  = distinct users from the cohort with an event in that month.
-- cohort_size   = users in the cohort.
-- retention_pct = 100 * active_users / cohort_size, rounded to 1 decimal.
-- Columns: cohort_month, month_number, active_users, cohort_size, retention_pct.
-- Order by cohort_month, month_number.

