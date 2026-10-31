{{ config(materialized='table') }}
-- One row per order, with what was paid and the customer's city.
SELECT
  o.order_id,
  o.customer_id,
  c.city,
  o.order_date,
  o.status,
  o.amount,
  COALESCE(p.paid_amount, 0) AS paid_amount,
  CASE WHEN o.status = 'delivered' THEN o.amount END AS revenue
FROM {{ ref('stg_orders') }} AS o
LEFT JOIN (
  SELECT order_id, SUM(paid_amount) AS paid_amount
  FROM {{ ref('stg_payments') }}
  GROUP BY order_id
) AS p ON p.order_id = o.order_id
LEFT JOIN {{ ref('stg_customers') }} AS c ON c.customer_id = o.customer_id
