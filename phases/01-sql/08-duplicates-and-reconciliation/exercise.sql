-- Lesson 08: duplicates and reconciliation. Your turn.
-- Tables:
--   crm_contacts(contact_id, email, full_name, signup_date, plan, updated_at, source)
--   app_signups(month, signups)   the app's own count of new accounts per month
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py
-- Try a query on its own first: python3 ../query.py "SELECT * FROM crm_contacts LIMIT 5"
--
-- The rules Mira agreed:
--   customer_key: the email with spaces trimmed, in lower case, and any +tag
--     before the @ removed (asha+webinar@x.example is asha@x.example).
--     A contact with no email is its own customer: key 'contact:' || contact_id.
--   The surviving row of each customer is the newest one (latest updated_at).
--     On a tie, the smallest contact_id.

-- query: survivors
-- TODO: one row per customer, the surviving row.
-- Columns: customer_key, contact_id, plan, signup_date.
-- Order by signup_date, then customer_key.


-- query: plan_counts
-- TODO: customers per plan, using each customer's surviving row.
-- Columns: plan, customers. Order by plan.


-- query: reconciliation
-- TODO: one row per signup month (YYYY-MM) that appears in the CRM or in app_signups.
-- Columns: month, crm_rows, unique_customers, app_signups,
--          difference (unique_customers - app_signups). Order by month.
-- A month missing on one side shows 0 for that side.
