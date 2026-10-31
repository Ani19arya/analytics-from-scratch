-- Lesson 10: sessionization from raw events. Your turn.
-- Table:
--   events(event_id, user_id, event_time, event_name)   event_time is 'YYYY-MM-DD HH:MM:SS', or NULL
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py
-- Try a query on its own first: python3 ../query.py "SELECT * FROM events LIMIT 5"
--
-- The rules Kofi agreed:
--   An event with no event_time cannot be placed in time: leave it out.
--   Order each user's events by event_time, then event_id.
--   A session starts at a user's first event, and whenever the gap since that
--   user's previous event is MORE than 30 minutes. A gap of exactly 30:00
--   stays in the same session.
--   Session length = last event time - first event time, in whole seconds.

-- query: sessionized_events
-- TODO: one row per event that has a time.
-- Columns: event_id, user_id, event_time, gap_seconds (NULL on a user's first
-- event), session_number (1, 2, 3 ... per user). Order by user_id, event_time, event_id.


-- query: sessions
-- TODO: one row per session.
-- Columns: user_id, session_number, start_time, end_time, events, duration_seconds.
-- Order by user_id, session_number.


-- query: user_summary
-- TODO: one row per user who has at least one session.
-- Columns: user_id, sessions, events, avg_duration_seconds (rounded to 1 decimal).
-- Order by user_id.
