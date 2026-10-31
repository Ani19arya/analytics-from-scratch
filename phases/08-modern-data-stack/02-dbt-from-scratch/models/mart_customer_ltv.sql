{{ config(materialized='view') }}
-- Lifetime revenue per customer, including customers who never ordered.
SELECT c.customer_id, c.signup_date, ROUND(COALESCE(SUM(f.revenue), 0), 2) AS lifetime_revenue
FROM {{ ref('stg_customers') }} AS c
LEFT JOIN {{ ref( "fct_orders" ) }} AS f ON f.customer_id = c.customer_id
GROUP BY c.customer_id, c.signup_date
