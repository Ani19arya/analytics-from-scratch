-- Lesson 02: SQL interview questions. Your turn.
-- Tables: employees(emp_id, name, department, salary)
--         signups(signup_id, email, signed_up_at)
--         logins(user_id, login_date)            login_date is 'YYYY-MM-DD'
--         orders(order_id, order_date, amount)   order_date is 'YYYY-MM-DD'
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py

-- query: second_highest_salary
-- TODO: the second highest DISTINCT salary. Two people share the top salary.
-- Columns: second_highest.


-- query: duplicate_emails
-- TODO: emails that signed up more than once, after LOWER and TRIM.
-- Columns: email (normalized), signups. Order by signups DESC, then email.


-- query: three_day_streaks
-- TODO: users who logged in on at least 3 consecutive calendar days, with their longest streak.
-- Some users log in several times a day: count distinct days.
-- Columns: user_id, longest_streak. Order by user_id.
-- Hint: julianday(login_date) - ROW_NUMBER() is constant inside a run of consecutive days.


-- query: top_two_per_department
-- TODO: in each department, everyone whose salary is one of the two highest salary levels.
-- Ties share a rank. Columns: department, name, salary, salary_rank.
-- Order by department, salary_rank, name.


-- query: running_total
-- TODO: for September 2026, one row per day that had orders: the day's revenue and the
-- running total since 1 September. Both rounded to 2 decimals.
-- Columns: order_date, revenue, running_total. Order by order_date.


-- query: month_over_month
-- TODO: one row per month from the first to the last month in orders, INCLUDING months
-- with no orders (revenue 0). Revenue rounded to 2 decimals, prev_revenue is the month
-- before, pct_change = 100 * (revenue - prev) / prev rounded to 1 decimal, NULL when prev
-- is NULL or 0. Columns: month ('YYYY-MM'), revenue, prev_revenue, pct_change. Order by month.
-- Hint: WITH RECURSIVE months(...) and strftime('%Y-%m', month || '-01', '+1 month').
