-- Lesson 11: gaps and islands: streaks. Your turn.
-- Table:
--   workouts(workout_id, user_id, logged_at, workout_type, minutes)
--   logged_at is 'YYYY-MM-DD HH:MM:SS' in the user's local time, or NULL
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py
-- Try a query on its own first: python3 ../query.py "SELECT * FROM workouts LIMIT 5"
--
-- The rules Amara agreed:
--   A workout day is a calendar day (the date part of logged_at) with at
--   least one workout. Two workouts on one day are one workout day.
--   A streak is a run of consecutive workout days. One day on its own is a
--   streak of 1. A row with no logged_at cannot be placed on a day: leave it out.

-- query: streaks
-- TODO: one row per streak.
-- Columns: user_id, streak_start, streak_end, days. Order by user_id, streak_start.


-- query: longest_streak
-- TODO: one row per user who has a workout day: their longest streak.
-- If two streaks are equally long, the earlier one.
-- Columns: user_id, longest_days, streak_start, streak_end. Order by user_id.


-- query: three_day_users
-- TODO: the users with at least one streak of 3 or more days, and how many such streaks.
-- Columns: user_id, streaks_3_plus. Order by user_id.
