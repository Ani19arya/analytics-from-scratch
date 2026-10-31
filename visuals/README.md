# Visual explainers

Five small interactive pages, each tied to one lesson. Each page uses that lesson's fictional company and its synthetic data, so the numbers you see are the numbers in the lesson.

## How to open them

Double-click a file, or open [index.html](index.html) and pick one. They are plain HTML, CSS and JavaScript in one file each. Nothing is loaded from the internet: no scripts, fonts, data or links, so they work offline and on a phone. They follow your system's light or dark setting, and every control works with the keyboard.

Each page checks its own math when it opens and prints the result at the bottom ("Self check: 24 of 24 ..."). The expected values are embedded in the page and come from the lesson itself: SQLite for the SQL pages, the lesson solutions for the A/B test and the agent loop.

## The pages

| Page | Lesson | What it teaches |
|---|---|---|
| [join-fanout.html](join-fanout.html) | [01-02 Joins without losing rows](../phases/01-sql/02-joins-without-losing-rows/) | Give a Brightcart customer a second address and the join turns one to many: the row count and SUM grow with no error. Predict the rows (left x right per key), then fix it by keeping one address per key, aggregating first, or joining to the DISTINCT keys. Ends with a planted fan-out to find. |
| [window-functions.html](window-functions.html) | [01-03 Window functions](../phases/01-sql/03-window-functions/) | Choose PARTITION BY, ORDER BY, the frame (ROWS or RANGE) and the function (running SUM, RANK, ROW_NUMBER, LAG) on Fernhill Supply's data, and see each row's value and the rows it uses. Shows the RANK vs ROW_NUMBER tie and why the default RANGE frame doubles a running total on ties. |
| [cohort-triangle.html](cohort-triangle.html) | [01-04 Cohort retention](../phases/01-sql/04-cohort-retention/) | Build Tallyo's retention triangle from 716 raw events. Switch months that have not happened from blank to 0 and watch the column averages fall; count events instead of users, or divide by last month, and see what breaks. Ends with a planted cell to click. |
| [ab-test.html](ab-test.html) | [02-03 A/B test from scratch](../phases/02-statistics-and-experiments/03-ab-test-from-scratch/) and [02-13 A/B test pitfalls](../phases/02-statistics-and-experiments/13-ab-test-pitfalls/) | Sliders for visitors and conversions per arm, with the pooled z-test, p-value, 95% interval on the lift and the sample ratio check, using the lesson's formulas. A seeded peeking simulation of A/A tests reproduces lesson 02-13's run (seed 0, 2000 tests) exactly. |
| [agent-loop.html](agent-loop.html) | [06-13 An analytics agent loop from scratch](../phases/06-ai-for-analysts/13-agent-loop-from-scratch/) | Step through Larkspur Goods agent runs one model call at a time: what the loop sends, the parse, the guard blocking a forbidden query, the observation, the growing token cost and the number grounding check. Then flag the ungrounded number yourself. The runs are the lesson's simulated fixture: no model was called. |

## Tests

`python3 -B -m unittest tools/test_visuals.py` (also run by the course's unittest discovery in CI) checks that every page is self-contained and offline, has a title, a language and a viewport, contains no forbidden characters, and that its embedded data matches the lesson's CSV files. It then recomputes every expected value in each page's fixtures block with its own Python code.

If a lesson's data changes, the test fails until the page's fixtures block is rebuilt from the new data.

`node tools/visuals_browser_test.mjs` opens every page in headless Chromium (Playwright) from a file:// URL. It fails on any console or page error or any request that is not file://, checks the "Self check: N of N" footer, drives the main controls (with the mouse and with the keyboard) and compares the numbers on screen with the page's fixtures block, and checks a 375 px wide phone layout with no sideways scroll, a different background in dark mode, an accessible name on every control and chart, and exactly one h1. CI runs it in the official Playwright container; locally it needs only `npm install --no-save playwright`.
