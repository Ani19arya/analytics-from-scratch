{{ config(materialized='view') }}
SELECT payment_id, order_id, method, CAST(amount AS REAL) AS paid_amount
FROM raw_payments
