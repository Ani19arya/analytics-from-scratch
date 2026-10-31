# Dashboards and spreadsheets

What Excel, Power BI and Tableau compute underneath, rebuilt and tested, plus how to design a chart or a dashboard for a decision.

**Complete beginner?** If you have never run a lesson, start with [phase 00, Start here](../00-start-here/). Lessons 01 to 03 here use SQL from [phase 01](../01-sql/); lesson 04 uses a little Python and says which parts.

## Lessons, in order

1. [Model the data a dashboard needs](01-model-the-data-a-dashboard-needs/) (level 2): a star schema with a fact table and date, product and region dimensions, an orders card that counts orders, not lines, and a calendar where Sunday shows 0.
2. [DAX measures from scratch](02-dax-measures-from-scratch/) (level 2): SUM, CALCULATE (which replaces a filter on the same column) and KEEPFILTERS (which intersects), a share that removes only the category filter, year to date and growth on the same period last year.
3. [Tableau LOD expressions in SQL](03-tableau-lod-expressions-in-sql/) (level 2): FIXED, INCLUDE and EXCLUDE rebuilt with GROUP BY and window functions, and Tableau's order of operations.
4. [Draw a chart from scratch](04-draw-a-chart-from-scratch/) (level 1): an SVG bar chart in plain Python, the truncated axis trap, and a first-pass rule set for choosing a chart.
5. Lookups and SUMIFS like Excel (level 1, planned)
6. Pivot tables and Power Query steps (level 1, planned)
7. Dashboard design and KPI cards (level 1, planned)
8. Relationships, role-playing dates and many-to-many (level 2, planned)
9. One metric, one definition: the semantic layer (level 2, planned)
10. Slowly changing dimensions (level 2, planned)
11. Row-level security (level 2, planned)
12. Tableau table calculations vs LOD (level 2, planned)

## How this phase teaches tools that live in a GUI

Excel, Power BI and Tableau are clicked, not scripted, and they cannot run inside an offline test. So every lesson follows the same honest pattern:

1. **Rebuild the logic and test it.** The lesson writes what the tool computes underneath, in sqlite3 SQL or standard library Python: the filter context of a DAX measure, the level of detail of a Tableau expression, the axis of a bar chart. `test_lesson.py` checks your version against answers computed independently in plain Python, on the committed data and on a second dataset built in memory.
2. **Show the tool next to it, as a reference.** The matching DAX, Tableau calculation or menu path sits beside the SQL or Python, labelled "reference only, not run in this course". Where a tool's behaviour matters (CALCULATE replacing a filter, FIXED running before dimension filters), the README cites the vendor's documentation with the date it was read.
3. **Optional: do it in the tool and check the numbers.** Where a lesson says so, build the same visual in Power BI, Tableau or Excel and compare it with the numbers the walk through prints. Lessons that work on spreadsheets will also accept a CSV you export from the tool and check it when it is there, and skip that check when it is not, so the course still runs with nothing installed.

Once you know what a measure, a level of detail expression or a bar chart computes, the tool is just the interface, and you can tell when it is showing you the wrong number.

Each live lesson has a `README.md` to read, an `exercise.sql` or `exercise.py` to fill in, and a `test_lesson.py`. Run `python3 test_lesson.py` from the lesson folder. The lessons follow [LESSON_TEMPLATE.md](../../LESSON_TEMPLATE.md).
