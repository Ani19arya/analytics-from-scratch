# Dashboards (Power BI and Tableau)

Power BI and Tableau cannot run inside an offline test, so this phase rebuilds what they do underneath in SQL and Python. Each lesson writes the logic the tool runs for you, in sqlite3 SQL or standard library Python, checks it with a test, and shows the matching DAX or Tableau calculation next to it as a reference block. Once you know what a measure, a level of detail expression or a bar chart computes, the tool is just the interface.

1. [Model the data a dashboard needs](01-model-the-data-a-dashboard-needs/): a star schema with a fact table and date, product and region dimensions.
2. [DAX measures from scratch](02-dax-measures-from-scratch/): SUM, a CALCULATE style filtered measure, year to date and growth on the same period last year.
3. [Tableau LOD expressions in SQL](03-tableau-lod-expressions-in-sql/): FIXED, INCLUDE and EXCLUDE rebuilt with GROUP BY and window functions.
4. [Draw a chart from scratch](04-draw-a-chart-from-scratch/): an SVG bar chart in plain Python, and the rules for choosing a chart.

The lessons follow the same format as the rest of the course (see [LESSON_TEMPLATE.md](../../LESSON_TEMPLATE.md)).
