{{ config(materialized='table') }}
SELECT city, COUNT(revenue) AS delivered_orders, ROUND(COALESCE(SUM(revenue), 0), 2) AS revenue
FROM {{ ref('fct_orders') }}
GROUP BY city
