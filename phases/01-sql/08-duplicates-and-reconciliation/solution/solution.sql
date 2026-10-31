-- Lesson 08: duplicates and reconciliation. Worked answer.
-- Tables:
--   crm_contacts(contact_id, email, full_name, signup_date, plan, updated_at, source)
--   app_signups(month, signups)   the app's own count of new accounts per month
--
-- The business key is the email, normalised: spaces trimmed, lower case, and
-- any "+tag" in the part before the @ removed. A contact with no email is its
-- own customer, keyed by its contact_id, so the NULLs are not lumped together.
-- The surviving row is the newest one (latest updated_at); on a tie, the
-- smallest contact_id.

-- query: survivors
WITH cleaned AS (
  SELECT *, lower(trim(email)) AS e
  FROM crm_contacts
),
keyed AS (
  SELECT *,
         CASE
           WHEN e IS NULL OR e = '' THEN 'contact:' || contact_id
           WHEN instr(e, '+') BETWEEN 1 AND instr(e, '@') THEN
             substr(e, 1, instr(e, '+') - 1) || substr(e, instr(e, '@'))
           ELSE e
         END AS customer_key
  FROM cleaned
),
ranked AS (
  SELECT *,
         ROW_NUMBER() OVER (PARTITION BY customer_key
                            ORDER BY updated_at DESC, contact_id) AS rn
  FROM keyed
)
SELECT customer_key, contact_id, plan, signup_date
FROM ranked
WHERE rn = 1
ORDER BY signup_date, customer_key;

-- query: plan_counts
WITH cleaned AS (
  SELECT *, lower(trim(email)) AS e
  FROM crm_contacts
),
keyed AS (
  SELECT *,
         CASE
           WHEN e IS NULL OR e = '' THEN 'contact:' || contact_id
           WHEN instr(e, '+') BETWEEN 1 AND instr(e, '@') THEN
             substr(e, 1, instr(e, '+') - 1) || substr(e, instr(e, '@'))
           ELSE e
         END AS customer_key
  FROM cleaned
),
ranked AS (
  SELECT *,
         ROW_NUMBER() OVER (PARTITION BY customer_key
                            ORDER BY updated_at DESC, contact_id) AS rn
  FROM keyed
)
SELECT plan, COUNT(*) AS customers
FROM ranked
WHERE rn = 1
GROUP BY plan
ORDER BY plan;

-- query: reconciliation
WITH cleaned AS (
  SELECT *, lower(trim(email)) AS e
  FROM crm_contacts
),
keyed AS (
  SELECT *,
         CASE
           WHEN e IS NULL OR e = '' THEN 'contact:' || contact_id
           WHEN instr(e, '+') BETWEEN 1 AND instr(e, '@') THEN
             substr(e, 1, instr(e, '+') - 1) || substr(e, instr(e, '@'))
           ELSE e
         END AS customer_key
  FROM cleaned
),
crm AS (
  SELECT substr(signup_date, 1, 7) AS month,
         COUNT(*) AS crm_rows,
         COUNT(DISTINCT customer_key) AS unique_customers
  FROM keyed
  GROUP BY substr(signup_date, 1, 7)
),
months AS (
  SELECT month FROM crm
  UNION
  SELECT month FROM app_signups
)
SELECT m.month,
       COALESCE(c.crm_rows, 0) AS crm_rows,
       COALESCE(c.unique_customers, 0) AS unique_customers,
       COALESCE(a.signups, 0) AS app_signups,
       COALESCE(c.unique_customers, 0) - COALESCE(a.signups, 0) AS difference
FROM months m
LEFT JOIN crm c ON c.month = m.month
LEFT JOIN app_signups a ON a.month = m.month
ORDER BY m.month;
