# Joins without losing rows

Which customers have never ordered, and what is revenue by city without counting any order twice?

## The problem

You work on the growth team at Brightcart, an online grocery. Dev, the CRM manager, wants a list of every customer who signed up this year but never placed an order, so he can send them a first-order coupon on Monday. Finance also wants revenue by customer city, and last month's version of that report came out higher than the actual order total. You have three tables: 120 customers, 360 orders and 154 saved addresses. Your job is to join them without silently dropping customers or silently duplicating orders.

## What you will build from scratch

- The row-count check: count each table, then count the join, and explain the difference.
- An inner join and a left join on the same keys, and a list of customers with no match.
- One row per customer with order count and total spend, zeros included.
- Revenue by city that adds up to the real order total, by fixing a fan-out.

The data in `data/` is synthetic. `make_data.py` builds it with a fixed random seed.

## The idea

A join pairs every row on the left with every row on the right whose key matches.

- **INNER JOIN** keeps only pairs. A customer with no orders has no pair, so the customer disappears.
- **LEFT JOIN** keeps every left row. If there is no match, the right side columns are NULL.

So you can predict the row count before you run anything:

```
inner rows = sum over keys of (left rows with key k) x (right rows with key k)
left rows  = inner rows + (left rows with no match)
```

Customers to orders is one to many. Each order matches exactly one customer, so the inner join has one row per order: 360. The 28 customers with no orders add one NULL row each to the left join: 360 + 28 = 388.

**Fan-out** happens when the right side has more than one row per key and you did not expect it. A customer with two saved addresses matches each order twice. `SUM(amount)` then counts that order twice. Nothing errors. The total is just wrong.

The analyst's habit: before you trust a join, compare the row count to what the key relationship says it should be. If a one to one join grows, a key is not unique.

## Walk through

Step 1. Count everything.

```sql
SELECT
  (SELECT COUNT(*) FROM customers) AS customers,
  (SELECT COUNT(*) FROM orders) AS orders,
  (SELECT COUNT(*) FROM customers c JOIN orders o ON o.customer_id = c.customer_id) AS inner_rows,
  (SELECT COUNT(*) FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id) AS left_rows;
```

This returns 120, 360, 360, 388.

Step 2. Find the customers with no match. After a left join, unmatched rows have NULL in every right side column, including the right side key.

```sql
SELECT c.customer_id
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
WHERE o.order_id IS NULL
ORDER BY c.customer_id;
```

Step 3. One row per customer. Count `o.order_id`, not `*`, because `COUNT(*)` would count the NULL row of a non-buyer as 1.

```sql
SELECT
  c.customer_id,
  COUNT(o.order_id) AS order_count,
  ROUND(COALESCE(SUM(o.amount), 0), 2) AS total_spent
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id
ORDER BY c.customer_id;
```

Step 4. See the fan-out. Join orders to addresses on customer_id alone.

```sql
SELECT COUNT(*) AS joined_rows, ROUND(SUM(o.amount), 2) AS revenue
FROM orders o
JOIN customer_addresses a ON a.customer_id = o.customer_id;
```

This returns 465 rows and 38399.54, but there are only 360 orders worth 29551.86. Customers with two addresses doubled their orders.

Step 5. Make the right side unique per key before or during the join. Here each customer has exactly one primary address, so put that condition in the ON clause.

```sql
SELECT a.city, ROUND(SUM(o.amount), 2) AS revenue
FROM orders o
JOIN customer_addresses a
  ON a.customer_id = o.customer_id
 AND a.is_primary = 1
GROUP BY a.city
ORDER BY a.city;
```

The five cities now add up to 29551.86.

## Your turn

Open `exercise.sql` and write the four queries: `row_counts`, `customer_totals`, `customers_without_orders` and `revenue_by_city`.

```
python3 test_lesson.py
```

Run it from this folder. The fan-out test checks that your city revenue adds up to the order total.

## Check yourself

1. A join between two tables of 1,000 rows returns 1,400 rows. What does that tell you?
2. Why is `COUNT(o.order_id)` correct after a LEFT JOIN and `COUNT(*)` wrong?
3. You put `WHERE o.amount > 50` after a LEFT JOIN. What happens to customers with no orders?
4. Two ways to fix a fan-out?

<details>
<summary>Answers</summary>

1. At least one join key is not unique on one side, so some rows matched more than once. Find the duplicated keys before using any SUM.
2. A non-buyer still produces one row, with NULLs on the right. `COUNT(*)` counts that row as 1. `COUNT(o.order_id)` skips NULLs and gives 0.
3. They disappear, because NULL > 50 is not true. The LEFT JOIN behaves like an INNER JOIN. Put the condition in the ON clause to keep them.
4. Make the right side one row per key first (filter, as with is_primary, or pre-aggregate in a subquery), or aggregate each table separately and join the totals.

</details>

## In real job postings

On 25 October 2026 the Real Analyst Jobs live feed had 1,193 India analyst postings, and 70% of the 914 that list tools ask for SQL. Read the full breakdown in [SQL skills for data analyst jobs](https://realanalystjobs.com/research/sql-skills-for-data-analyst-jobs).

## Next

[03 Window functions](../03-window-functions/)
