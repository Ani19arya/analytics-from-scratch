# Reshape wide and long

The data has one row per region and month. The manager wants one row per region. How do you move between the two without losing anything?

## The problem

Larkspur Coffee, a fictional chain with four regions, keeps its revenue as one row per region and month. Tom, the operations director, wants a table for Monday's review with regions down the side and months across the top, the way he reads it. The same afternoon, the BI team asks for the file back in the original shape so their dashboard can load it. You need both shapes, built from the same numbers, with nothing dropped or invented on the way.

The file `data/sales_long.csv` (23 rows) is synthetic, built by `make_data.py` with a fixed random seed. West has no March row on purpose: that store was closed for a refit.

## What you will build from scratch

- `pivot_wider`: long to wide, with empty cells where a pair is missing and an error when a pair appears twice.
- `pivot_longer`: wide back to long, skipping empty cells, so the round trip gives back the exact input.
- `total_by`: a group sum that shows why tools prefer long data.

## The idea

**Long** data has one row per observation: `region, month, revenue`. **Wide** data has one row per entity and one column per value of some variable: `region, Jan, Feb, Mar, ...`.

People want wide tables because the eye compares across a row. Tools want long data because every question is the same loop. Total by month, total by region, average by region: in long form each is "group by one column, sum another". In wide form the months are column names, so the code has to know them, and a new month means new code.

**Long to wide** is a dictionary keyed by pairs:

```
cells[(row_key, column_key)] = value
```

Read every row once, keep the row keys and column keys in the order they first appear, then build one output row per row key, looking up each column. A pair that is not in `cells` becomes an empty cell. A pair that arrives twice is an error, not an overwrite: if two rows claim to be North in January, one of them is wrong, and silently keeping the last one hides that.

**Wide to long** is the reverse loop: for every row, for every column that is not the ID, emit `(id, column, value)`. Skip empty cells, so a missing value stays missing instead of turning into a row with no number.

**Empty is not zero.** West's March cell is empty because the store was closed. If you fill it with 0, the wide table says West sold nothing in March, which is a different claim. Note what this does to totals: March is 165,792 across all regions, well below February's 206,914, because only three regions report. That is a missing store, not a bad month. Say so next to the number.

## Walk through

Store cells by pair, then read them back:

```python
rows = [
    {"region": "North", "month": "Jan", "revenue": "46000"},
    {"region": "North", "month": "Feb", "revenue": "46845"},
    {"region": "West", "month": "Jan", "revenue": "46000"},
]
cells = {(r["region"], r["month"]): r["revenue"] for r in rows}
print(cells.get(("West", "Feb"), ""))
print(cells[("North", "Feb")])
```

The first line prints an empty line, because West has no February in this sample. The second prints `46845`.

Unpivot one wide row:

```python
wide_row = {"region": "West", "Jan": "46000", "Feb": "47005", "Mar": ""}
print([(wide_row["region"], k, v) for k, v in wide_row.items() if k != "region" and v != ""])
```

March is skipped, so the result has two tuples, not three.

Run the worked answer:

```
python3 solution/solution.py
```

It prints the wide table (4 regions by 6 months, with West March empty), unpivots it back to 23 rows that equal the input row for row, and totals revenue by month with one call to `total_by`.

## Your turn

Open `exercise.py`. Fill in `pivot_wider`, `pivot_longer` and `total_by`. Keep everything as strings except inside `total_by`, where you convert to `int` to add. Then run, from this folder:

```
python3 test_lesson.py
```

## Check yourself

1. A dashboard tool asks for data. Do you send it wide or long, and why?
2. Your pivot has two input rows for North in January. What should happen?
3. Why does `pivot_longer` skip empty cells instead of writing a 0?
4. In Excel this is a pivot table. In SQL, which clause does the long-form `total_by` correspond to?

<details>
<summary>Answers</summary>

1. Long. Every chart and filter in the tool can then group by any column, and a new month is a new row, not a new column the tool has to be told about.
2. Raise an error. Either the data has a real duplicate or the key is missing a column, such as a store inside the region. Summing or keeping the last row would both hide the problem.
3. Empty means not observed. Zero means observed and nothing happened. Writing 0 changes the meaning and drags down any average.
4. `GROUP BY` with `SUM`, for example `SELECT month, SUM(revenue) FROM sales GROUP BY month`.

</details>

## In real job postings

Reshaping is where Excel and Python meet. On the Real Analyst Jobs live feed read on 25 October 2026, 72% of the 2,102 US analyst postings that list tools ask for SQL and 48% ask for Python. See the [Excel skills page](https://realanalystjobs.com/skills/excel), or turn nested JSON into a flat table with the [JSON to CSV converter](https://realanalystjobs.com/tools/json-csv-converter).

## Next

[03 Dates, weeks and time zones](../03-dates-weeks-and-time-zones/)
