-- Lesson 05: dates and the date spine. Worked answer.
-- Tables:
--   signups(user_id, signed_up_at_utc)      text 'YYYY-MM-DD HH:MM:SS', in UTC
--   report_period(start_date, end_date)     one row, text 'YYYY-MM-DD', IST days
--
-- The team reads days in India time, IST = UTC + 5 hours 30 minutes.
-- date(signed_up_at_utc, '+330 minutes') is the IST calendar day of a signup.
-- The date spine is a list of every day in the period, built with a
-- recursive CTE, so a day with no signups is still a row (with 0).

-- query: daily_signups
WITH RECURSIVE spine(day) AS (
  -- the first day of the period
  SELECT start_date FROM report_period
  UNION ALL
  -- then the day after, until the last day of the period
  SELECT date(spine.day, '+1 day')
  FROM spine, report_period
  WHERE spine.day < report_period.end_date
),
ist AS (
  -- each signup on the IST calendar
  SELECT user_id, date(signed_up_at_utc, '+330 minutes') AS day
  FROM signups
)
SELECT spine.day, COUNT(ist.user_id) AS signups
FROM spine
LEFT JOIN ist ON ist.day = spine.day
GROUP BY spine.day
ORDER BY spine.day;

-- query: zero_days
WITH RECURSIVE spine(day) AS (
  SELECT start_date FROM report_period
  UNION ALL
  SELECT date(spine.day, '+1 day')
  FROM spine, report_period
  WHERE spine.day < report_period.end_date
)
SELECT spine.day
FROM spine
WHERE NOT EXISTS (
  SELECT 1 FROM signups s
  WHERE date(s.signed_up_at_utc, '+330 minutes') = spine.day
)
ORDER BY spine.day;

-- query: summary
WITH RECURSIVE spine(day) AS (
  SELECT start_date FROM report_period
  UNION ALL
  SELECT date(spine.day, '+1 day')
  FROM spine, report_period
  WHERE spine.day < report_period.end_date
),
daily AS (
  SELECT spine.day, COUNT(s.user_id) AS signups
  FROM spine
  LEFT JOIN signups s ON date(s.signed_up_at_utc, '+330 minutes') = spine.day
  GROUP BY spine.day
)
SELECT
  COUNT(*) AS days,
  SUM(signups) AS signups,
  ROUND(1.0 * SUM(signups) / COUNT(*), 2) AS avg_per_day
FROM daily;
