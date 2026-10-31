-- Lesson 02: funnel conversion. Your turn.
-- Table: events(user_id, event_name, event_time)   event_time is text 'YYYY-MM-DD HH:MM:SS'
-- Steps in order: view_course, add_to_cart, begin_checkout, purchase
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py

-- query: events_per_step
-- TODO: for each event_name, the number of events and the number of distinct users.
-- Columns: event_name, events, users. Order by funnel step (view_course first).
-- Hint: ORDER BY CASE event_name WHEN 'view_course' THEN 1 ... END


-- query: funnel
-- TODO: one row per step with the users who reached it IN ORDER.
-- A user reaches step n if they did every step 1..n, and the first time they did
-- each step is at or after the first time they did the step before it.
-- step_conversion_pct    = 100 * users / users at the previous step (100.0 for step 1)
-- overall_conversion_pct = 100 * users / users at step 1
-- Both rounded to 1 decimal.
-- Columns: step_number, step, users, step_conversion_pct, overall_conversion_pct.
-- Order by step_number.
-- Hint: MIN(CASE WHEN event_name = '...' THEN event_time END) per user, then a
-- 0/1 flag per step with CASE WHEN ... THEN 1 ELSE 0 END, then
-- LAG() and FIRST_VALUE() over (ORDER BY step_number).


-- query: biggest_drop
-- TODO: the single step-to-step transition with the lowest step conversion.
-- Columns: from_step, to_step, users_lost, step_conversion_pct (1 decimal).
-- users_lost = users at from_step - users at to_step.
-- On a tie (two transitions with the same rounded step_conversion_pct), return the earlier one.
