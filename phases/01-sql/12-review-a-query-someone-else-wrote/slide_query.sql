-- October 2026 city performance for the Monday review.
-- Drafted by Rahul with an AI assistant, and pasted into the slide as is.
-- Completed orders only. Orders paid with a staff promo code are left out
-- (they are internal, not real demand).
SELECT c.city,
       COUNT(DISTINCT o.order_id) AS orders,
       SUM(i.qty) AS items,
       SUM(o.amount) AS revenue,
       SUM(o.amount) / COUNT(DISTINCT o.order_id) AS avg_order_value,
       SUM(i.qty) / COUNT(DISTINCT o.order_id) AS items_per_order
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN order_items i ON i.order_id = o.order_id
LEFT JOIN promo_redemptions p ON p.order_id = o.order_id
WHERE o.status = 'completed'
  AND o.ordered_at BETWEEN '2026-10-01' AND '2026-10-31'
  AND p.channel <> 'staff'
GROUP BY c.city
ORDER BY revenue DESC;
