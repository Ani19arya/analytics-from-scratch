-- Lesson 04: cohort retention. Your turn.
-- Tables:
--   users(user_id, signup_date)    dates are text 'YYYY-MM-DD'
--   events(user_id, event_date)
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py
-- Try a query on its own first: python3 ../query.py "SELECT * FROM users LIMIT 5"

-- query: cohort_sizes
-- TODO: number of users per signup month.
-- Columns: cohort_month ('YYYY-MM'), users. Order by cohort_month.
-- Hint: strftime('%Y-%m', signup_date)


-- query: retention
-- TODO: the retention table in long form.
-- month_number = calendar months between the signup month and the event month
--   (0 = the signup month, 1 = the next calendar month, ...).
--   Careful at the year end: December 2025 to January 2026 is 1 month.
-- One row per cohort and every month_number from 0 up to the last month the
-- data can show for that cohort. The data ends in the month of the latest
-- event in events. A month where nobody from the cohort was active is a row
-- with active_users 0. Months after the data ends get no row at all.
-- active_users  = distinct users from the cohort with an event in that month.
-- cohort_size   = all users in the cohort (from users, not from events).
-- retention_pct = 100 * active_users / cohort_size, rounded to 1 decimal.
-- Columns: cohort_month, month_number, active_users, cohort_size, retention_pct.
-- Order by cohort_month, month_number.
-- You may assume every calendar month up to the end of the data has at least
-- one event from someone.


