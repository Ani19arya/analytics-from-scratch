# Analytics from Scratch

Learn data analytics by building every method yourself, from raw rows and the formula, before any tool does it for you.

## Why

Most analyst courses teach you where to click in a tool. This one teaches you what the tool is doing.

Every lesson is a business problem with a named stakeholder and a deadline. You get the math or the SQL logic written out, an exercise to fill in, and a test that tells you when your answer is right.

- Standard library Python 3.9 or later, plus the built-in `sqlite3`. No pip installs.
- Runs offline. No accounts, no API keys, no network.
- Every dataset is small and rebuilt the same way each time by its lesson's `make_data.py`.
- Free and open source under the MIT license.

Read the whole course online, one page per lesson: https://realanalystjobs.com/learn

## Quick start

```
git clone https://github.com/Ani19arya/analytics-from-scratch
cd analytics-from-scratch/phases/01-sql/01-group-by-from-raw-rows
python3 test_lesson.py
```

The test fails until you complete `exercise.sql`. Read the lesson `README.md`, fill in the exercise, and run the test again.

To check every lesson's worked solution from the repo root:

```
python3 tools/run_all_tests.py
```

Add `--exercise` to also confirm each shipped exercise still fails, as it should.

## Learn with your coding agent

The repo ships a tutor skill for coding agents that read SKILL.md files (Claude Code, Cursor, Codex and others):

```
npx skills add Ani19arya/analytics-from-scratch
```

Then open your agent inside a clone of this repo and ask it to tutor you through analytics from scratch. It places you with three questions, picks a starting lesson, and gives hints before answers. See [skills/README.md](skills/README.md) for the manual install.

## Curriculum

| # | Phase | Status |
|---|---|---|
| 01 | [SQL from raw tables](phases/01-sql) | 4 lessons |
| 02 | [Statistics and experiments](phases/02-statistics-and-experiments) | 4 lessons |
| 03 | [Metrics and product analytics](phases/03-metrics-and-product-analytics) | 4 lessons |
| 04 | [Dashboards (Power BI and Tableau)](phases/04-dashboards) | 4 lessons |
| 05 | [Python for analysts](phases/05-python-for-analysts) | 4 lessons |
| 06 | [AI for analysts](phases/06-ai-for-analysts) | 3 lessons |
| 07 | [Getting hired](phases/07-getting-hired) | 4 lessons |

### 01 SQL from raw tables

1. [GROUP BY from raw rows](phases/01-sql/01-group-by-from-raw-rows): How much did each city bring in last quarter, and which cities are big enough to matter?
2. [Joins without losing rows](phases/01-sql/02-joins-without-losing-rows): Which customers have never ordered, and what is revenue by city without counting any order twice?
3. [Window functions](phases/01-sql/03-window-functions): How is each region tracking against its year to date, who are the top reps, and did revenue go up or down from last month?
4. [Cohort retention](phases/01-sql/04-cohort-retention): Of the users who signed up in each month, what share were still active one, two and three months later?

### 02 Statistics and experiments

1. [Mean, median and skew](phases/02-statistics-and-experiments/01-mean-median-and-skew): What is the typical posted pay for an analyst role, and which number should we put on the slide?
2. [Confidence interval by hand](phases/02-statistics-and-experiments/02-confidence-interval-by-hand): How sure are we about an average or a rate measured on a sample?
3. [A/B test from scratch](phases/02-statistics-and-experiments/03-ab-test-from-scratch): Did the new checkout page really convert better, or did we get lucky?
4. [Sample size before you test](phases/02-statistics-and-experiments/04-sample-size-before-you-test): How many users, and how many weeks, do we need before an A/B test can answer the question we care about?

### 03 Metrics and product analytics

1. [Metric trees](phases/03-metrics-and-product-analytics/01-metric-trees): Revenue fell this week, so which part of the business made it fall?
2. [Funnel conversion](phases/03-metrics-and-product-analytics/02-funnel-conversion): Of the people who look at a course, how many buy it, and at which step do we lose the most of them?
3. [Active users and stickiness](phases/03-metrics-and-product-analytics/03-active-users-and-stickiness): How many people really use the app, and how often do they come back?
4. [North star and guardrails](phases/03-metrics-and-product-analytics/04-north-star-and-guardrails): The new feature moved our main metric up, so should we launch it?

### 04 Dashboards (Power BI and Tableau)

1. [Model the data a dashboard needs](phases/04-dashboards/01-model-the-data-a-dashboard-needs): How do you turn one flat export of order lines into tables a dashboard can slice by date, product and region without double counting?
2. [DAX measures from scratch](phases/04-dashboards/02-dax-measures-from-scratch): What does a Power BI measure actually compute, and how do you get the same Total Sales, filtered sales, year to date and growth on last year numbers without Power BI?
3. [Tableau LOD expressions in SQL](phases/04-dashboards/03-tableau-lod-expressions-in-sql): How do you compute a number at a different level of detail from the chart it sits in, such as each customer's first order month in a chart by month, or a region's total in a chart by customer?
4. [Draw a chart from scratch](phases/04-dashboards/04-draw-a-chart-from-scratch): What does a dashboard tool do when it turns a table into a bar chart, and which chart should you pick in the first place?

Power BI and Tableau cannot run inside an offline test, so this phase rebuilds what they do underneath in SQL and Python, with the DAX and Tableau versions shown next to each one.

### 05 Python for analysts

1. [Clean a messy CSV](phases/05-python-for-analysts/01-clean-a-messy-csv): Which rows of this export can we trust, and what did we change to get there?
2. [Reshape wide and long](phases/05-python-for-analysts/02-reshape-wide-and-long): The data has one row per region and month. The manager wants one row per region. How do you move between the two without losing anything?
3. [Dates, weeks and time zones](phases/05-python-for-analysts/03-dates-weeks-and-time-zones): How many people signed up each week over the new year, counted on the clock the team actually works on?
4. [Automate the weekly report](phases/05-python-for-analysts/04-automate-the-weekly-report): Can the Monday KPI report write itself, with the same numbers every time it runs?

### 06 AI for analysts

1. [Grade an LLM classifier](phases/06-ai-for-analysts/01-grade-an-llm-classifier): Is the LLM good enough at spotting refund tickets that we can route them automatically?
2. [Check LLM-written SQL](phases/06-ai-for-analysts/02-check-llm-written-sql): Which of the queries the LLM wrote can we trust, and which ones would have put a wrong number in the report?
3. [Catch made-up numbers](phases/06-ai-for-analysts/03-catch-made-up-numbers): Every number in the AI-written summary: is it actually in the data?

The AI lessons call no API. The model outputs are saved fixtures, so they run offline like the rest.

### 07 Getting hired

1. [Read job postings like data](phases/07-getting-hired/01-read-job-postings-like-data): Across 300 analyst job postings, which tools are asked for most, how much experience do they want, and what do they say about visa sponsorship?
2. [SQL interview questions](phases/07-getting-hired/02-sql-interview-questions): Can you answer the six SQL questions that come up again and again in analyst interviews, and explain why the obvious answer is wrong?
3. [Portfolio project end to end](phases/07-getting-hired/03-portfolio-project-end-to-end): Do customers who start on a free trial cancel within 90 days more often than customers who pay from day one?
4. [Match your resume to a posting](phases/07-getting-hired/04-match-your-resume-to-a-posting): Of five open roles, which ones fit this resume best, and which missing skills stand between the candidate and the rest?

## Open job-market data

[data/job-market](data/job-market) holds a monthly snapshot of the analyst job market, built from the live Real Analyst Jobs feed. Unlike the lesson datasets, which are synthetic, these files are real aggregates. They hold counts only, with no company level or job level rows:

- `by_country.csv`: postings and distinct hiring companies per country.
- `by_country_skill.csv`: how often postings list SQL, Python, Excel, Tableau, Power BI, Looker, R and dbt.
- `by_country_seniority.csv`: postings per experience level.

A new `YYYY-MM/` folder is added every month, and older folders are never edited. You can rebuild a month yourself with `tools/build_job_market_snapshot.py`. The method and limitations are in [data/job-market/README.md](data/job-market/README.md). The data is licensed CC BY 4.0.

## Built by Real Analyst Jobs

This course is made by [Real Analyst Jobs](https://realanalystjobs.com), a job board for data and business analyst roles collected from company career pages. Each lesson ends with a short section on what real job postings ask for, with a dated number from the live feed, so you can see how the skill you just built shows up in hiring.

## Contributing

New lessons follow one format: a business problem, the idea from first principles, a walk through, an exercise that fails as shipped, a solution, and a stdlib test. See [LESSON_TEMPLATE.md](LESSON_TEMPLATE.md) for the files, sections and style rules.

To propose a lesson, open an issue with the business question, the phase it belongs to, and the method it teaches. Bug reports and fixes to existing lessons are welcome too.

## License

- Code and lessons: MIT. See [LICENSE](LICENSE).
- Job-market data in `data/job-market`: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Credit it as: Real Analyst Jobs (realanalystjobs.com).
