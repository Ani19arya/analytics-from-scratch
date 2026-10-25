-- Lesson 02: SQL interview questions. Reference solution.
-- Tables: employees(emp_id, name, department, salary)
--         signups(signup_id, email, signed_up_at)
--         logins(user_id, login_date)
--         orders(order_id, order_date, amount)

-- query: second_highest_salary
SELECT MAX(salary) AS second_highest
FROM employees
WHERE salary < (SELECT MAX(salary) FROM employees);

-- query: duplicate_emails
SELECT LOWER(TRIM(email)) AS email, COUNT(*) AS signups
FROM signups
GROUP BY LOWER(TRIM(email))
HAVING COUNT(*) > 1
ORDER BY signups DESC, email;

-- query: three_day_streaks
WITH days AS (
  SELECT DISTINCT user_id, login_date FROM logins
),
islands AS (
  SELECT user_id, login_date,
         julianday(login_date) - ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) AS grp
  FROM days
),
streaks AS (
  SELECT user_id, grp, COUNT(*) AS streak_days FROM islands GROUP BY user_id, grp
)
SELECT user_id, MAX(streak_days) AS longest_streak
FROM streaks
GROUP BY user_id
HAVING MAX(streak_days) >= 3
ORDER BY user_id;

-- query: top_two_per_department
WITH ranked AS (
  SELECT department, name, salary,
         DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS salary_rank
  FROM employees
)
SELECT department, name, salary, salary_rank
FROM ranked
WHERE salary_rank <= 2
ORDER BY department, salary_rank, name;

-- query: running_total
WITH daily AS (
  SELECT order_date, ROUND(SUM(amount), 2) AS revenue
  FROM orders
  WHERE order_date BETWEEN '2026-09-01' AND '2026-09-30'
  GROUP BY order_date
)
SELECT order_date, revenue,
       ROUND(SUM(revenue) OVER (ORDER BY order_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS running_total
FROM daily
ORDER BY order_date;

-- query: month_over_month
WITH RECURSIVE months(month) AS (
  SELECT MIN(substr(order_date, 1, 7)) FROM orders
  UNION ALL
  SELECT strftime('%Y-%m', month || '-01', '+1 month') FROM months
  WHERE month < (SELECT MAX(substr(order_date, 1, 7)) FROM orders)
),
revenue AS (
  SELECT substr(order_date, 1, 7) AS month, SUM(amount) AS revenue FROM orders GROUP BY 1
),
filled AS (
  SELECT months.month, ROUND(COALESCE(revenue.revenue, 0), 2) AS revenue
  FROM months LEFT JOIN revenue ON revenue.month = months.month
)
SELECT month, revenue,
       LAG(revenue) OVER (ORDER BY month) AS prev_revenue,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
             / NULLIF(LAG(revenue) OVER (ORDER BY month), 0), 1) AS pct_change
FROM filled
ORDER BY month;
