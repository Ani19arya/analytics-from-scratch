# Cohort retention

Of the users who signed up in each month, what share were still active one, two and three months later?

## The problem

You are the product analyst at Tallyo, a budgeting app. Sam, the product manager, wants to know whether the onboarding change shipped in April kept new users around longer, and the board deck is due next Wednesday. A single "monthly active users" number cannot answer that, because it mixes old and new users. You have two raw tables: 298 users with their signup date, and 716 activity events from January to June 2026. You will group users into monthly signup cohorts and build the retention table in SQL.

## What you will build from scratch

- Monthly signup cohorts with `strftime('%Y-%m', ...)`.
- A month number for every event: how many calendar months after signup it happened.
- Active users per cohort and month with `COUNT(DISTINCT ...)`.
- Retention as a percentage of cohort size, in long form and as a pivoted table.

The data in `data/` is synthetic. `make_data.py` builds it with a fixed random seed. Data stops at 30 June 2026, so later cohorts have fewer months to show.

## The idea

A cohort is a group of users who share a starting point. Here the starting point is the signup month.

For each user u and each event e:

```
cohort(u)       = signup month of u
month_number(e) = (event_year - signup_year) * 12 + (event_month - signup_month)
```

Month 0 is the signup month. Month 1 is the next calendar month, whatever day the user signed up.

Then, for each cohort c and month number m:

```
active_users(c, m)  = number of DISTINCT users in c with at least one event in month m
retention_pct(c, m) = 100 * active_users(c, m) / cohort_size(c)
```

Two traps decide whether the table is right:

1. **Count users, not events.** A user with two events in a month is still one retained user. `COUNT(*)` on events inflates retention.
2. **Divide by the cohort size, not by last month's actives.** Retention compares each month to the starting group. Every row of a cohort uses the same denominator.

## Walk through

Step 1. Cohort sizes.

```sql
SELECT strftime('%Y-%m', signup_date) AS cohort_month, COUNT(*) AS users
FROM users
GROUP BY cohort_month
ORDER BY cohort_month;
```

January has 42 users, February 52, March 51, April 55, May 58 and June 40.

Step 2. Turn every event into a (user, cohort, month number) row, with duplicates removed. SQLite has no month difference function, so build it from the year and month parts.

```sql
SELECT DISTINCT
  u.user_id,
  strftime('%Y-%m', u.signup_date) AS cohort_month,
  (CAST(strftime('%Y', e.event_date) AS INTEGER) - CAST(strftime('%Y', u.signup_date) AS INTEGER)) * 12
    + CAST(strftime('%m', e.event_date) AS INTEGER) - CAST(strftime('%m', u.signup_date) AS INTEGER)
    AS month_number
FROM users u
JOIN events e ON e.user_id = u.user_id
ORDER BY u.user_id, month_number
LIMIT 10;
```

Step 3. Count distinct users per cohort and month, and divide by the cohort size. The full query is in `solution/solution.sql` once you have tried it. Its shape is three CTEs: `cohorts`, `activity` (step 2) and `sizes` (step 1), then a final GROUP BY.

Step 4. Read the result as a triangle. Pivot the long rows with conditional aggregation.

```sql
WITH activity AS (
  SELECT DISTINCT
    u.user_id,
    strftime('%Y-%m', u.signup_date) AS cohort_month,
    (CAST(strftime('%Y', e.event_date) AS INTEGER) - CAST(strftime('%Y', u.signup_date) AS INTEGER)) * 12
      + CAST(strftime('%m', e.event_date) AS INTEGER) - CAST(strftime('%m', u.signup_date) AS INTEGER)
      AS month_number
  FROM users u
  JOIN events e ON e.user_id = u.user_id
)
SELECT
  cohort_month,
  COUNT(DISTINCT CASE WHEN month_number = 0 THEN user_id END) AS m0,
  ROUND(100.0 * COUNT(DISTINCT CASE WHEN month_number = 1 THEN user_id END)
        / COUNT(DISTINCT CASE WHEN month_number = 0 THEN user_id END), 1) AS m1_pct,
  ROUND(100.0 * COUNT(DISTINCT CASE WHEN month_number = 2 THEN user_id END)
        / COUNT(DISTINCT CASE WHEN month_number = 0 THEN user_id END), 1) AS m2_pct,
  ROUND(100.0 * COUNT(DISTINCT CASE WHEN month_number = 3 THEN user_id END)
        / COUNT(DISTINCT CASE WHEN month_number = 0 THEN user_id END), 1) AS m3_pct
FROM activity
GROUP BY cohort_month
ORDER BY cohort_month;
```

This divides by the month 0 actives, which equals the cohort size here only because every user has an event on their signup day. In your own data, check that before relying on it.

| cohort | users | month 1 | month 2 | month 3 |
|---|---|---|---|---|
| 2026-01 | 42 | 57.1% | 35.7% | 26.2% |
| 2026-02 | 52 | 61.5% | 36.5% | 28.8% |
| 2026-03 | 51 | 56.9% | 25.5% | 17.6% |
| 2026-04 | 55 | 60.0% | 43.6% | |
| 2026-05 | 58 | 65.5% | | |
| 2026-06 | 40 | | | |

The blank cells are months that have not happened yet. They are not zero retention. Read down a column to compare cohorts at the same age: April's month 2 retention of 43.6% is the highest so far, but it is one cohort of 55 users, so treat it as a lead, not a result.

## Your turn

Open `exercise.sql` and write `cohort_sizes` and `retention`. The retention query returns the long form: one row per cohort and month number.

```
python3 test_lesson.py
```

Run it from this folder. One test checks that month 0 equals the cohort size, which fails if you count events instead of distinct users.

## Check yourself

1. Why is a retention table better than a monthly active users chart for judging an onboarding change?
2. A user signs up on 31 January and comes back on 1 February. Which month number is that event?
3. What goes wrong if you divide by the previous month's active users?
4. Why are the bottom right cells of the triangle empty?

<details>
<summary>Answers</summary>

1. Active users mix every cohort together, so a large new cohort can hide that each cohort is leaving faster. Cohorts compare users at the same age.
2. Month 1. Calendar month retention counts the month boundary, not 30 days. If you need day based retention, use day 30, day 60 and so on, and say which one you used.
3. You get month to month survival, not retention. The numbers look healthier and are not comparable across cohorts of different sizes.
4. Those cohorts are too young. The data ends in June, so the May cohort can only have months 0 and 1.

</details>

## In real job postings

On 25 October 2026 the Real Analyst Jobs live feed had 2,848 US analyst postings, and 72% of the 2,102 that list tools ask for SQL. The [SQL skills for data analyst jobs](https://realanalystjobs.com/research/sql-skills-for-data-analyst-jobs) study has more on how SQL shows up in analyst postings.

## Next

Phase 01 is done. Go on to [Phase 02: Statistics and experiments](../../02-statistics-and-experiments/).
