# Tableau LOD expressions in SQL

How do you compute a number at a different level of detail from the chart it sits in, such as each customer's first order month in a chart by month, or a region's total in a chart by customer?

## The problem

You are the analyst at Kestrel Outdoor, a shop that sells hiking gear to 120 customers in three regions: Alpine, Coast and Lakes. Sofia, the marketing manager, has a Tableau workbook with three questions she cannot get right before Friday's campaign review: how many new customers arrived each month, how much a typical customer spends in each region, and what share of the region's sales each month and each customer brings. Her first try counted distinct customers per month, which counts every returning customer again. Tableau answers these with level of detail (LOD) expressions. You will rebuild each one in SQL, so you know exactly what the workbook should show.

## What you will build from scratch

- `FIXED` at customer: each customer's first order month, and new customers per month from it.
- `INCLUDE` customer: the average customer's total sales in each region, which is not the average order.
- `EXCLUDE` month: each month's share of its region's full year.
- `FIXED` at region in a view by customer: each customer's share of their region.

The data in `data/` is synthetic. `make_data.py` builds it with a fixed random seed: 459 orders in 2025 from 120 customers.

## The idea

Every Tableau view has a **level of detail**: the dimensions on rows, columns and marks. A plain `SUM([Amount])` is computed at that level. An LOD expression computes an aggregate at a level you name, then hands the result back to the view.

- `{FIXED [Customer ID] : MIN([Order Date])}` computes at exactly the dimensions listed, whatever the view shows. In SQL: a `GROUP BY customer_id` subquery, then join or aggregate its result.
- `{INCLUDE [Customer ID] : SUM([Amount])}` computes at the view's dimensions plus the one listed. In a view by region, that is one value per region and customer, which the view then aggregates again (for example with AVG). In SQL: `GROUP BY region, customer_id` in an inner query, then `GROUP BY region` with `AVG` outside.
- `{EXCLUDE [Month] : SUM([Amount])}` computes at the view's dimensions minus the one listed. In a view by region and month, it is the region total repeated on every month row. In SQL: `SUM(sales) OVER (PARTITION BY region)`, a window that keeps the rows.

The general rule: a level of detail is a GROUP BY. A coarser level that must sit next to finer rows is a window function with `PARTITION BY` the coarser columns. A finer level that must be rolled up is a subquery with an extra GROUP BY column.

One difference to know for interviews: in Tableau, `FIXED` is computed before ordinary dimension filters, so filtering the view to Coast does not change a FIXED value unless you make that filter a context filter. `INCLUDE` and `EXCLUDE` respect the filters. In SQL you get the same effect by choosing whether the WHERE clause sits inside or outside the subquery.

## Walk through

Step 1. FIXED at customer. Customer C001 ordered four times, first in November 2025, so the first order month is `2025-11` on every one of C001's rows.

```sql
SELECT customer_id, MIN(substr(order_date, 1, 7)) AS first_order_month
FROM orders
GROUP BY customer_id
ORDER BY customer_id
```

Step 2. New customers per month. Count customers by their first month. Compare it with distinct customers per month: February 2025 had 17 active customers but only 13 new ones.

```sql
SELECT first_order_month, COUNT(*) AS new_customers
FROM (
  SELECT customer_id, MIN(substr(order_date, 1, 7)) AS first_order_month
  FROM orders
  GROUP BY customer_id
) firsts
GROUP BY first_order_month
ORDER BY first_order_month
```

```sql
SELECT substr(order_date, 1, 7) AS year_month, COUNT(DISTINCT customer_id) AS active_customers
FROM orders
GROUP BY year_month
ORDER BY year_month
```

Step 3. INCLUDE customer. `AVG(amount)` by region is the average order: 135.80 in Alpine. The average customer spent 526.65 there, because customers place several orders. Sum per customer first, then average.

```sql
SELECT region, COUNT(*) AS customers, ROUND(AVG(customer_sales), 2) AS avg_customer_sales
FROM (
  SELECT region, customer_id, SUM(amount) AS customer_sales
  FROM orders
  GROUP BY region, customer_id
) per_customer
GROUP BY region
ORDER BY region
```

Step 4. EXCLUDE month. Group to region and month, then put the region total on every row with a window. Alpine's year is 21,592.84, and January 2025 is 0.0214 of it.

```sql
SELECT region, year_month, ROUND(sales, 2) AS sales,
  ROUND(SUM(sales) OVER (PARTITION BY region), 2) AS region_sales,
  ROUND(sales / SUM(sales) OVER (PARTITION BY region), 4) AS pct_of_region
FROM (
  SELECT region, substr(order_date, 1, 7) AS year_month, SUM(amount) AS sales
  FROM orders
  GROUP BY region, year_month
) monthly
ORDER BY region, year_month
```

Step 5. FIXED at region in a view by customer. The same window, one level down. C092 is Alpine's biggest customer at 1,582.27, which is 0.0733 of the region.

```sql
SELECT customer_id, region, ROUND(customer_sales, 2) AS customer_sales,
  ROUND(SUM(customer_sales) OVER (PARTITION BY region), 2) AS region_sales,
  ROUND(customer_sales / SUM(customer_sales) OVER (PARTITION BY region), 4) AS share_of_region
FROM (
  SELECT customer_id, region, SUM(amount) AS customer_sales
  FROM orders
  GROUP BY customer_id, region
) per_customer
ORDER BY region, customer_sales DESC, customer_id
```

### The same calculations in Tableau (reference only, not run in this course)

```tableau
// Step 1: First Order Month (put it on Columns, COUNTD([Customer ID]) on Rows for step 2)
DATETRUNC('month', {FIXED [Customer ID] : MIN([Order Date])})

// Step 3: in a view with Region on Rows, use AVG of this field
{INCLUDE [Customer ID] : SUM([Amount])}

// Step 4: in a view with Region and MONTH([Order Date])
SUM([Amount]) / SUM({EXCLUDE MONTH([Order Date]) : SUM([Amount])})

// Step 5: in a view with Customer ID
SUM([Amount]) / SUM({FIXED [Region] : SUM([Amount])})
```

Power BI does the same with `CALCULATE` and filter removal: `ALLEXCEPT(orders, orders[region])` plays the part of FIXED at region.

## Your turn

Open `exercise.sql` and write `customer_first_month`, `new_customers_by_month`, `avg_customer_sales_by_region`, `region_month_share` and `customer_share_of_region`.

```
python3 test_lesson.py
```

Run it from this folder. The test recomputes each level of detail with Python dictionaries over the raw orders.

## Check yourself

1. What is the difference between FIXED, INCLUDE and EXCLUDE?
2. Why is the average customer's sales different from the average order value?
3. You filter a Tableau view to one region and a FIXED value does not change. Why, and how do you make it change?
4. How would you write `{EXCLUDE [Month] : SUM([Amount])}` in SQL without a window function?

<details>
<summary>Answers</summary>

1. FIXED computes at exactly the dimensions you list and ignores the view. INCLUDE computes at the view's dimensions plus the ones you list, so it is finer than the view. EXCLUDE computes at the view's dimensions minus the ones you list, so it is coarser.
2. Customers place more than one order. The order average divides total sales by orders, the customer average divides by customers. In Alpine that is 135.80 against 526.65.
3. FIXED is computed before ordinary dimension filters. Add the filter to context (it then runs before FIXED), or use INCLUDE or EXCLUDE, which respect it. In SQL, the filter must sit inside the subquery that does the FIXED grouping.
4. Compute region totals in a GROUP BY region subquery and join it back to the region and month rows on region.

</details>

## In real job postings

On 25 October 2026 the Real Analyst Jobs live feed had 2,848 US analyst postings. Of the 2,102 that list tools, 36% ask for Tableau and 24% for Power BI, so Tableau leads in the US. See the [Tableau skills page](https://realanalystjobs.com/skills/tableau) and the [US analyst job market study](https://realanalystjobs.com/research/us-analyst-job-market-october-2026).

## Next

[04 Draw a chart from scratch](../04-draw-a-chart-from-scratch/)
