-- Lesson 05: dates and the date spine. Your turn.
-- Tables:
--   signups(user_id, signed_up_at_utc)      text 'YYYY-MM-DD HH:MM:SS', in UTC
--   report_period(start_date, end_date)     one row, text 'YYYY-MM-DD', IST days
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py
-- Try a query on its own first: python3 ../query.py "SELECT * FROM signups LIMIT 5"
--
-- Days are India days (IST = UTC + 5 hours 30 minutes):
--   date(signed_up_at_utc, '+330 minutes') is the IST day of a signup.

-- query: daily_signups
-- TODO: one row for EVERY day from start_date to end_date (both included),
-- including days with no signups, which show 0.
-- Columns: day ('YYYY-MM-DD'), signups. Order by day.
-- Hint: build the list of days with WITH RECURSIVE (a date spine), then
-- LEFT JOIN the signups to it. Count a column from signups, not *.


-- query: zero_days
-- TODO: the days of the period with no signups at all.
-- Columns: day. Order by day.


-- query: summary
-- TODO: one row for the whole period.
-- Columns: days (days in the period), signups (signups in the period),
--   avg_per_day = signups / days, rounded to 2 decimals.
-- Zero days count as days.
