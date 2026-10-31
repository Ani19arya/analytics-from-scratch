# Deliverables: what to hand in

Part of capstone [10-05](README.md). Read [BRIEF.md](BRIEF.md) first.

## 1. The model and the numbers with one right answer (checked by the test)

Fill in every function in `exercise.py`, then run `python3 test_lesson.py` from this folder. The test checks your model and KPIs on the committed data, on a second dataset built from another seed, and on small hand-made tables. Use these definitions; they are the ones the dashboard will be held to, and the test uses them too.

| Term | Definition |
|---|---|
| Clean shop-day | One row per (`sales_date`, `store_id`): the send with the latest `loaded_at` |
| Net revenue of a shop-day | `gross_sales - discounts` before 2026-07-01; `gross_sales` from 2026-07-01. No rounding per row |
| `dim_date` | One row per calendar day from the first to the last sales date, no gaps: `date_key`, `month` (YYYY-MM), `year`, `day_of_week` (0 = Monday), `is_weekend` (1 on Saturday and Sunday) |
| `fact_sales` | One row per clean shop-day: `date_key`, `store_id`, `orders`, `net_revenue`, `cogs`. The grain is (date_key, store_id) |
| Model checks | No duplicate grain; every fact date in `dim_date`; every fact and target shop in `dim_store`; no negative value; no sales before a shop opened or on a closure day; no gap in `dim_date` |
| Missing day | A day in the month on which a shop had opened, was not in a closure, and has no `fact_sales` row |
| Net revenue, orders | Sums over the month's `fact_sales` rows |
| AOV (average order value) | Net revenue / orders, over the whole month (not an average of shop or daily AOVs) |
| Gross margin % | 100 x (net revenue - cogs) / net revenue, over the whole month |
| Target, % of target | Sum of `revenue_target` for the month; 100 x net revenue / target |
| Status | green at 100% of target or more, amber from 95% to under 100%, red below 95%, none without a target |
| Year on year (YoY) % | 100 x (net revenue / net revenue of the same month a year earlier - 1), all shops |
| Like-for-like (LFL) shops | Shops opened on or before the first day of the same month a year earlier, with no closure day in either month |
| LFL growth % | YoY % over LFL shops only |
| Rounding | Money and percentages to 2 decimals; any ratio with a zero or missing denominator is None |

## 2. The model, documented

Half a page a reviewer can check: the tables, the grain of each, how they join (a diagram is welcome), and the output of your model checks on the committed data. Name every cleaning rule and where it lives in your code.

## 3. The dashboard

One screen for September 2026, in any tool: Power BI, Tableau, Looker Studio, a spreadsheet, or standard-library SVG like `solution/dashboard.svg`. It must have:

- four KPI cards: net revenue against target with its status, LFL growth, gross margin, AOV with orders;
- a 13-month net revenue trend, September 2025 to September 2026, axis from zero;
- a shop table: net revenue, % of target with status, gross margin;
- a visible note when data is missing, and a note that the data is synthetic.

If you build it in a BI tool, load the clean model, not the raw files (`solution/solution.py` writes one to `solution/model/` if you want to compare with yours). Export the tool's September card values to `exports/kpis_from_tool.csv` with columns `kpi,value` and rows `net_revenue`, `orders`, `gross_margin_pct`, `lfl_growth_pct`; the test then checks your tool against the model.

## 4. A metric sheet

One line per KPI on the dashboard: name, definition in plain words, formula, and one known limit. This is what ends the spreadsheet arguments, so write it for the shop managers.

## 5. A note for Hannah

Half a page to send with the dashboard link:

1. How September went, in two sentences, with the numbers she will see on the cards.
2. The answer to "are we actually growing?", with the like-for-like number and why it differs from +23%.
3. Where margin is hurting.
4. What is missing or uncertain this month and how it affects the cards.
5. One recommendation with an owner and a date.

Score it all with [RUBRIC.md](RUBRIC.md). Then read [solution/WRITEUP.md](solution/WRITEUP.md) and compare.
