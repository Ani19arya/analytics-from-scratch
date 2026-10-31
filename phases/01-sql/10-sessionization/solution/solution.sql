-- Lesson 10: sessionization from raw events. Worked answer.
-- Table:
--   events(event_id, user_id, event_time, event_name)   event_time is 'YYYY-MM-DD HH:MM:SS', or NULL
--
-- The rules:
--   An event with no event_time cannot be placed in time: leave it out.
--   Order each user's events by event_time, then event_id.
--   A session starts at a user's first event, and whenever the gap since that
--   user's previous event is MORE than 30 minutes (1800 seconds). A gap of
--   exactly 1800 seconds stays in the same session.
--   Session length = last event time - first event time, in whole seconds.
--
-- Gaps are worked out in whole seconds with strftime('%s'), not with
-- julianday() * 86400: julianday is a fraction of a day, and a pause of
-- exactly 1800 seconds can come back as 1800.00004, which splits a session.

-- query: sessionized_events
WITH timed AS (
  SELECT event_id, user_id, event_time,
         CAST(strftime('%s', event_time) AS INTEGER) AS ts
  FROM events
  WHERE event_time IS NOT NULL
),
gaps AS (
  SELECT *, ts - LAG(ts) OVER (PARTITION BY user_id ORDER BY ts, event_id) AS gap_seconds
  FROM timed
),
flagged AS (
  SELECT *, CASE WHEN gap_seconds IS NULL OR gap_seconds > 1800 THEN 1 ELSE 0 END AS new_session
  FROM gaps
)
SELECT event_id, user_id, event_time, gap_seconds,
       SUM(new_session) OVER (PARTITION BY user_id ORDER BY ts, event_id
                              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS session_number
FROM flagged
ORDER BY user_id, ts, event_id;

-- query: sessions
WITH timed AS (
  SELECT event_id, user_id, event_time,
         CAST(strftime('%s', event_time) AS INTEGER) AS ts
  FROM events
  WHERE event_time IS NOT NULL
),
gaps AS (
  SELECT *, ts - LAG(ts) OVER (PARTITION BY user_id ORDER BY ts, event_id) AS gap_seconds
  FROM timed
),
numbered AS (
  SELECT *,
         SUM(CASE WHEN gap_seconds IS NULL OR gap_seconds > 1800 THEN 1 ELSE 0 END)
           OVER (PARTITION BY user_id ORDER BY ts, event_id
                 ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS session_number
  FROM gaps
)
SELECT user_id, session_number,
       MIN(event_time) AS start_time,
       MAX(event_time) AS end_time,
       COUNT(*) AS events,
       MAX(ts) - MIN(ts) AS duration_seconds
FROM numbered
GROUP BY user_id, session_number
ORDER BY user_id, session_number;

-- query: user_summary
WITH timed AS (
  SELECT event_id, user_id, event_time,
         CAST(strftime('%s', event_time) AS INTEGER) AS ts
  FROM events
  WHERE event_time IS NOT NULL
),
gaps AS (
  SELECT *, ts - LAG(ts) OVER (PARTITION BY user_id ORDER BY ts, event_id) AS gap_seconds
  FROM timed
),
numbered AS (
  SELECT *,
         SUM(CASE WHEN gap_seconds IS NULL OR gap_seconds > 1800 THEN 1 ELSE 0 END)
           OVER (PARTITION BY user_id ORDER BY ts, event_id
                 ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS session_number
  FROM gaps
),
sessions AS (
  SELECT user_id, session_number, COUNT(*) AS events, MAX(ts) - MIN(ts) AS duration_seconds
  FROM numbered
  GROUP BY user_id, session_number
)
SELECT user_id, COUNT(*) AS sessions, SUM(events) AS events,
       ROUND(AVG(duration_seconds), 1) AS avg_duration_seconds
FROM sessions
GROUP BY user_id
ORDER BY user_id;
