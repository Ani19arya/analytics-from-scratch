# Python for analysts

Cleaning, reshaping, profiling, APIs, charts and automation in standard library Python, with the bridge to pandas.

**Complete beginner?** If you have never run a Python file, go to [phase 00, Start here](../00-start-here/) first. It shows how to run a lesson and walks through your first Python script.

This phase uses only the Python standard library: `csv`, `datetime`, `re`, `zoneinfo` and plain dictionaries. No pandas. That is on purpose. Every step pandas does for you in one call, such as parsing dates, pivoting a table or grouping by week, is written out here by hand, so you see the decisions hidden inside those calls and can tell when a library made the wrong one. Each lesson runs on Python 3.9 or later with nothing to install.

## Lessons, in order

1. [Clean a messy CSV](01-clean-a-messy-csv/) (level 1)
2. [Reshape wide and long](02-reshape-wide-and-long/) (level 1)
3. [Dates, weeks and time zones](03-dates-weeks-and-time-zones/) (level 2)
4. [Automate the weekly report](04-automate-the-weekly-report/) (level 2)
5. [Profile a table before you trust it](05-profile-a-table/) (level 1)
6. [Join two files and prove nothing was lost](06-join-files-and-prove-nothing-was-lost/) (level 1)
7. [APIs and JSON](07-apis-and-json/) (level 2)
8. [More charts from scratch](08-more-charts-from-scratch/) (level 2)
9. [Data quality tests as code](09-data-quality-tests-as-code/) (level 2)
10. [From standard library to pandas](10-from-stdlib-to-pandas/) (level 2)

Each live lesson has a `README.md` to read, an `exercise.py` to fill in, and a `test_lesson.py` that checks your work on the lesson's data and on a second dataset built in memory. Run `python3 test_lesson.py` from the lesson folder.
