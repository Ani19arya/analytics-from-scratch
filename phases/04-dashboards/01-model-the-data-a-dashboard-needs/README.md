# Model the data a dashboard needs

How do you turn one flat export of order lines into tables a dashboard can slice by date, product and region without double counting?

## The problem

You are the analyst at Larkspur Home, an online homeware shop with four sales regions. Hana, the head of operations, wants a Power BI dashboard of revenue by month, category and region by the end of next week. The order system gives you one wide export, `transactions`, with the product name, category, region and region manager repeated on every order line. Last time someone pointed the dashboard straight at that export, the monthly chart skipped every Sunday and a "count of orders" card double counted orders with several lines. Before anyone drags a field onto a chart, you will build a proper star schema.

## What you will build from scratch

- A date dimension with one row per calendar day, including days with no sales.
- A product dimension and a region dimension, each with an integer surrogate key.
- A fact table at the grain of one row per order line, holding only keys and numbers.
- The first dashboard visual, revenue by month and category, built from the star schema.
- Checks that the model's totals match the raw export exactly.

The data in `data/` is synthetic. `make_data.py` builds it with a fixed random seed: 1,241 order lines from 620 orders across 2025, with no shipments on Sundays.

## The idea

A dashboard tool like Power BI or Tableau works best on a **star schema**: one fact table in the middle and several dimension tables around it.

```
               dim_date
                  |
dim_product --- fact_sales --- dim_region
```

- **Fact table.** One row per event you measure. Its columns are foreign keys to dimensions plus numeric columns you add up (quantity, revenue).
- **Dimension table.** One row per thing you filter or group by (a day, a product, a region). Its columns are descriptive text and attributes (category, manager, month name).
- **Grain.** The sentence that says what one fact row is. Here: "one row per order line". Write it down first. Every check below follows from it: the fact table must have exactly as many rows as the raw export has order lines, and `(order_id, line_no)` must be unique.

Why bother, when the flat table already has every column?

1. **Filters flow one way.** A slicer on `dim_product[category]` filters the fact rows through the key. With one flat table, every visual carries every repeated column.
2. **Dimensions hold rows the facts do not.** A date table must contain every day, so a chart of daily revenue shows Sunday as zero instead of skipping it, and year to date logic (next lesson) has a continuous calendar to walk.
3. **Totals stay honest.** If the fact table is at the right grain, `SUM(revenue)` over any slice equals the same slice of the raw data. That is the test you run every time you change the model.

A **surrogate key** is an integer you assign (1, 2, 3, ...) instead of joining on text. It keeps the fact table small and survives a product being renamed.

## Walk through

Step 1. Check the grain of the raw data. If `(order_id, line_no)` is unique, the raw table is at order line grain already.

```sql
SELECT COUNT(*) AS line_rows, COUNT(DISTINCT order_id || '-' || line_no) AS unique_lines, COUNT(DISTINCT order_id) AS orders
FROM transactions
```

Both counts are 1,241, and there are 620 orders. A fact table grouped by `order_id` would have 620 rows and would lose the product on every line.

Step 2. Build the date dimension with a recursive CTE. `SELECT DISTINCT order_date` would give only the 313 days with sales. The calendar from 1 January to 31 December 2025 has 365.

```sql
CREATE TABLE dim_date AS
WITH RECURSIVE days(date) AS (
  SELECT MIN(order_date) FROM transactions
  UNION ALL
  SELECT date(date, '+1 day') FROM days
  WHERE date < (SELECT MAX(order_date) FROM transactions)
)
SELECT
  CAST(strftime('%Y%m%d', date) AS INTEGER) AS date_key,
  date,
  CAST(strftime('%Y', date) AS INTEGER) AS year,
  (CAST(strftime('%m', date) AS INTEGER) + 2) / 3 AS quarter,
  CAST(strftime('%m', date) AS INTEGER) AS month,
  strftime('%Y-%m', date) AS year_month
FROM days
```

```sql
SELECT COUNT(*) AS days, MIN(date), MAX(date) FROM dim_date
```

Step 3. Build the product and region dimensions. `DISTINCT` collapses the repeated text, and `ROW_NUMBER()` hands out the surrogate key.

```sql
CREATE TABLE dim_product AS
SELECT ROW_NUMBER() OVER (ORDER BY product) AS product_key, product, category
FROM (SELECT DISTINCT product, category FROM transactions)
```

```sql
CREATE TABLE dim_region AS
SELECT ROW_NUMBER() OVER (ORDER BY region) AS region_key, region, region_manager
FROM (SELECT DISTINCT region, region_manager FROM transactions)
```

That gives 10 products and 4 regions. If a product appeared with two categories, `DISTINCT` would return two rows for it and the key would no longer identify one product. Count the rows against `COUNT(DISTINCT product)` to catch that.

Step 4. Build the fact table. Swap every piece of text for its key and keep the numbers.

```sql
CREATE TABLE fact_sales AS
SELECT
  t.order_id, t.line_no, d.date_key, p.product_key, r.region_key, t.quantity,
  ROUND(t.quantity * t.unit_price, 2) AS revenue
FROM transactions t
JOIN dim_date d ON d.date = t.order_date
JOIN dim_product p ON p.product = t.product
JOIN dim_region r ON r.region = t.region
```

Step 5. Reconcile. The model must give the same totals as the raw export: 3,152 units and 194,175.25 of revenue. If an inner join had dropped rows (say a product missing from `dim_product`), this is where you would see it.

```sql
SELECT COUNT(*) AS fact_rows, SUM(quantity) AS units, ROUND(SUM(revenue), 2) AS revenue FROM fact_sales
```

Step 6. Build the visual from the model. This is what a matrix with `year_month` on rows and `category` on columns asks the engine for.

```sql
SELECT d.year_month, p.category, ROUND(SUM(f.revenue), 2) AS revenue
FROM fact_sales f
JOIN dim_date d ON d.date_key = f.date_key
JOIN dim_product p ON p.product_key = f.product_key
GROUP BY d.year_month, p.category
ORDER BY d.year_month, p.category
```

### The same model in Power BI (reference only, not run in this course)

In Power BI you load `transactions` in Power Query, use Reference to make the product and region tables, Remove Duplicates on them, and draw one to many relationships from each dimension to the fact table. The date table is usually a DAX calculated table, which you then mark as the date table:

```dax
Date =
ADDCOLUMNS (
    CALENDAR ( MIN ( transactions[order_date] ), MAX ( transactions[order_date] ) ),
    "Year", YEAR ( [Date] ),
    "Quarter", QUARTER ( [Date] ),
    "Month", MONTH ( [Date] ),
    "YearMonth", FORMAT ( [Date], "YYYY-MM" )
)
```

`CALENDAR` does what the recursive CTE does: it returns every day between two dates, sales or not. In Tableau you would build the same relationships on the Data Source page.

## Your turn

Open `exercise.sql` and write `dim_date`, `dim_product`, `dim_region`, `fact_sales` and `revenue_by_category_month`. The test runs each of the first four as `CREATE TABLE <name> AS <your query>`, so write plain SELECT queries, without the CREATE TABLE line.

```
python3 test_lesson.py
```

Run it from this folder. The test checks the calendar has no gaps, the keys are unique, the fact table is at order line grain, every key resolves, and the totals match the raw export by region and by month and category.

## Check yourself

1. What is the grain of a fact table, and why do you decide it first?
2. Why does a date dimension need days with no sales?
3. When would you store a measure on a dimension instead of a fact table?
4. Your fact table has 1,180 rows and the raw export has 1,241. What do you check first?

<details>
<summary>Answers</summary>

1. The grain is what one row of the fact table represents, for example one order line. Every join, key and total depends on it. If you mix grains, such as order lines and order headers in one table, sums double count.
2. Charts by day or week would skip those days instead of showing zero, and time intelligence such as year to date and same period last year needs a continuous calendar to shift along.
3. Almost never. Numbers you add up belong in the fact table. A dimension can hold fixed attributes such as a product's list price or a region's target, but you then aggregate them with care because they repeat per dimension row, not per event.
4. The inner joins. Some raw rows have a product, region or date that is missing from a dimension, so the join dropped them. Find them with a LEFT JOIN and a `WHERE key IS NULL` filter.

</details>

## In real job postings

On 25 October 2026 the Real Analyst Jobs live feed had 1,193 India analyst postings. Of the 914 that list tools, 39% ask for Power BI and 34% for Tableau, and SQL leads at 70%. See the [Power BI skills page](https://realanalystjobs.com/skills/power-bi).

## Next

[02 DAX measures from scratch](../02-dax-measures-from-scratch/)
