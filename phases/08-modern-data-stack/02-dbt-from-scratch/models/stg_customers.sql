{{ config(materialized='view') }}
-- One row per customer, in theory. The CRM export is not deduplicated here.
SELECT customer_id, TRIM(city) AS city, signup_date
FROM raw_customers
