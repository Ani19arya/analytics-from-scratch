-- Lesson 11: gaps and islands: streaks. Worked answer.
-- Table:
--   workouts(workout_id, user_id, logged_at, workout_type, minutes)
--   logged_at is 'YYYY-MM-DD HH:MM:SS' in the user's local time, or NULL
--
-- A streak is a run of consecutive calendar days with at least one workout.
-- Two workouts on one day are one day of the streak, so the logs are cut down
-- to one row per user and day BEFORE numbering. Then, inside a streak, the day
-- and the row number go up together, so day minus row number is the same date
-- for every day of the streak: that date names the island.

-- query: streaks
WITH days AS (
  SELECT DISTINCT user_id, date(logged_at) AS day
  FROM workouts
  WHERE logged_at IS NOT NULL
),
islands AS (
  SELECT user_id, day,
         date(day, '-' || ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY day) || ' days') AS island
  FROM days
)
SELECT user_id, MIN(day) AS streak_start, MAX(day) AS streak_end, COUNT(*) AS days
FROM islands
GROUP BY user_id, island
ORDER BY user_id, streak_start;

-- query: longest_streak
WITH days AS (
  SELECT DISTINCT user_id, date(logged_at) AS day
  FROM workouts
  WHERE logged_at IS NOT NULL
),
islands AS (
  SELECT user_id, day,
         date(day, '-' || ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY day) || ' days') AS island
  FROM days
),
streaks AS (
  SELECT user_id, MIN(day) AS streak_start, MAX(day) AS streak_end, COUNT(*) AS days
  FROM islands
  GROUP BY user_id, island
),
ranked AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY days DESC, streak_start) AS rn
  FROM streaks
)
SELECT user_id, days AS longest_days, streak_start, streak_end
FROM ranked
WHERE rn = 1
ORDER BY user_id;

-- query: three_day_users
WITH days AS (
  SELECT DISTINCT user_id, date(logged_at) AS day
  FROM workouts
  WHERE logged_at IS NOT NULL
),
islands AS (
  SELECT user_id, day,
         date(day, '-' || ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY day) || ' days') AS island
  FROM days
),
streaks AS (
  SELECT user_id, island, COUNT(*) AS days
  FROM islands
  GROUP BY user_id, island
)
SELECT user_id, COUNT(*) AS streaks_3_plus
FROM streaks
WHERE days >= 3
GROUP BY user_id
ORDER BY user_id;
