# GROUP BY from raw rows

How much did each city bring in last quarter, and which cities are big enough to matter?

## The problem

You are the first analyst at Brightcart, a small online grocery that ships in five cities. The operations lead, Maya, needs completed revenue by city for the third quarter before Friday's planning meeting. She also wants a short list of the cities with at least 70 completed orders, because only those get a second delivery van. The data is one raw table of 400 orders, including refunded and cancelled ones that must not count as revenue. You will answer with three GROUP BY queries and prove the totals with a plain Python loop.

## What you will build from scratch

- A count of orders per status, so you know what you are filtering out.
- Completed orders, revenue and average order value per city with `COUNT`, `SUM` and `AVG`.
- A filtered list of cities using `HAVING`, and the reason it is not `WHERE`.
- The same totals computed in a Python loop, so you can see what GROUP BY does under the hood.

The data in `data/orders.csv` is synthetic. `make_data.py` builds it with a fixed random seed, so everyone gets the same 400 rows.

## The idea

GROUP BY is a loop with a dictionary. The database does four steps in this order:

1. `FROM orders` reads every row.
2. `WHERE status = 'completed'` throws away rows before any grouping happens.
3. `GROUP BY city` puts each remaining row into a bucket keyed by its city.
4. The aggregate functions collapse each bucket to one number:
   - `COUNT(*)` = number of rows in the bucket
   - `SUM(amount)` = amount_1 + amount_2 + ... + amount_n
   - `AVG(amount)` = SUM(amount) / COUNT(amount)
5. `HAVING` filters the buckets after they are collapsed. It can use `COUNT(*)` because by then the count exists. `WHERE` runs before the buckets exist, so it cannot.

Every column in the SELECT list must be either a GROUP BY key or an aggregate. If you select `order_date` without aggregating it, there is no single date for a bucket of 109 orders.

## Walk through

Step 1. Look at the statuses first. You cannot filter what you have not seen.

```sql
SELECT status, COUNT(*) AS orders
FROM orders
GROUP BY status
ORDER BY status;
```

This returns 21 cancelled, 340 completed and 39 refunded orders.

Step 2. Do the city totals by hand in Python. Run this from the lesson folder.

```python
import csv

buckets = {}
with open("data/orders.csv", newline="") as f:
    for row in csv.DictReader(f):
        if row["status"] != "completed":   # this is WHERE
            continue
        b = buckets.setdefault(row["city"], {"orders": 0, "revenue": 0.0})  # this is GROUP BY
        b["orders"] += 1                     # COUNT(*)
        b["revenue"] += float(row["amount"]) # SUM(amount)

for city in sorted(buckets):
    b = buckets[city]
    print(city, b["orders"], round(b["revenue"], 2), round(b["revenue"] / b["orders"], 2))
```

Austin comes out at 109 completed orders and 10004.56 in revenue.

Step 3. Write the same thing in SQL.

```sql
SELECT
  city,
  COUNT(*) AS orders,
  ROUND(SUM(amount), 2) AS revenue,
  ROUND(AVG(amount), 2) AS avg_order
FROM orders
WHERE status = 'completed'
GROUP BY city
ORDER BY city;
```

The numbers match the loop. That match is the habit to keep: when a total matters, check it a second way.

Step 4. Filter the groups with HAVING. Leeds has exactly 60 completed orders and Perth has 19, so a threshold of 70 keeps three cities.

```sql
SELECT city, COUNT(*) AS orders, ROUND(SUM(amount), 2) AS revenue
FROM orders
WHERE status = 'completed'
GROUP BY city
HAVING COUNT(*) >= 70
ORDER BY revenue DESC;
```

## Your turn

Open `exercise.sql` and write the three queries under their markers: `status_counts`, `city_totals` and `busy_cities`. The test builds the expected answers with a Python loop and compares them to your results.

```
python3 test_lesson.py
```

Run it from this folder. All three tests pass when your queries are right.

## Check yourself

1. What is the difference between WHERE and HAVING?
2. Why does `COUNT(amount)` sometimes differ from `COUNT(*)`?
3. You select `city, customer_id, SUM(amount)` but group only by `city`. What is wrong?
4. Average order value: is `AVG(amount)` the same as `SUM(amount) / COUNT(*)`?

<details>
<summary>Answers</summary>

1. WHERE filters rows before grouping. HAVING filters groups after the aggregates are computed, so it can use `COUNT(*)` or `SUM(...)`.
2. `COUNT(amount)` skips rows where amount is NULL. `COUNT(*)` counts every row.
3. `customer_id` is neither a group key nor an aggregate, so a city bucket has many values for it. Most databases reject the query. SQLite returns an arbitrary one, which is worse because it looks fine.
4. Only when no amount is NULL. AVG ignores NULLs in both the sum and the count, while `COUNT(*)` counts them.

</details>

## In real job postings

On 25 October 2026 the Real Analyst Jobs live feed had 2,848 US analyst postings, and 72% of the 2,102 that list tools ask for SQL. See which roles ask for it on the [SQL skills page](https://realanalystjobs.com/skills/sql).

## Next

[02 Joins without losing rows](../02-joins-without-losing-rows/)
