{{ config(materialized='view') }}
SELECT order_id, customer_id, order_date, LOWER(TRIM(status)) AS status, CAST(amount AS REAL) AS amount
FROM raw_orders
