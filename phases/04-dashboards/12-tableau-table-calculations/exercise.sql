-- Lesson 12: Tableau table calculations vs LOD. Your turn.
-- Table: sales(line_id, order_date 'YYYY-MM-DD', region, category, amount)
-- Each query is the table behind one Tableau view. Decide for each column whether
-- it is computed before or after the view's filters, then write it.
-- Write one query under each "-- query:" marker. Keep the markers.
-- Run from this folder: python3 test_lesson.py

-- query: running_total_by_month
-- TODO: RUNNING_SUM(SUM([Amount])) in a view of region by month, computed along the months.
-- Columns: region, year_month ('YYYY-MM'), sales, running_sales (both rounded to 2).
-- Order by region, year_month.


-- query: category_rank_by_region
-- TODO: rank the categories by sales within each region. Highest = 1. Ties share a
-- rank and the next rank is skipped (1, 1, 3). Rank on sales rounded to 2.
-- Columns: region, category, sales (rounded to 2), sales_rank.
-- Order by region, sales_rank, category.


-- query: share_with_region_filter
-- TODO: a view of category, filtered to region = 'Coast' with an ordinary dimension filter.
-- pct_of_view: percent of total as a table calculation.
-- pct_of_all_regions: SUM([Amount]) / SUM({FIXED : SUM([Amount])}).
-- Columns: category, sales (rounded to 2), pct_of_view, pct_of_all_regions (both rounded to 4).
-- Order by category.


-- query: running_total_q2
-- TODO: the view of step one, showing only 2026-04 to 2026-06.
-- running_dimension_filter: the months are removed by a dimension filter.
-- running_table_calc_filter: the months are hidden by a table calculation filter.
-- Columns: region, year_month, sales, running_dimension_filter, running_table_calc_filter
-- (all money rounded to 2). Order by region, year_month.
