# Automate the weekly report

Can the Monday KPI report write itself, with the same numbers every time it runs?

## The problem

Brightloom, a fictional online stationery shop, sends a KPI note to its founders every Monday. Leila, the analyst, spends an hour each week copying numbers from an export into a document, and twice this quarter a number was pasted into the wrong row. The founders want the note to look the same every week, cover the last full Monday to Sunday, and compare each number with the week before. Your job is a script that reads the order export, computes four KPIs and writes the note as a Markdown file, so Monday becomes one command.

The file `data/orders.csv` (485 orders, Monday 5 to Sunday 25 October 2026) is synthetic, built by `make_data.py` with a fixed random seed.

## What you will build from scratch

- `latest_complete_week`: finds the Monday of the last full week in the data.
- `rows_in_week` and `compute_kpis`: revenue, paid orders, average order value and refund rate for one week.
- `pct_change` and `format_change`: week-over-week change that never divides by zero and reports a rate in points.
- `build_report`: the Markdown note, the same layout every week.

## The idea

A report script is four steps, each one a function you can test on its own: **pick the period, filter, compute, write**.

**Pick the period.** The default is the last complete week, not "the last 7 days". Find the last Sunday on or before the latest date in the data, then go back 6 days to its Monday. If the export stops on a Wednesday, the report covers the week before, instead of comparing three days with seven.

**Define each KPI once, in code.**

```
revenue             = sum of amount over paid orders
paid orders         = count of paid orders
average order value = revenue / paid orders
refund rate         = refunded orders / all orders * 100
```

Write the definitions under the table too. A number that people read every week needs its definition next to it.

**Change.** For amounts and counts, use percent change: `(this - last) / last * 100`. It is undefined when last week is 0, so the cell says `n/a`. For a rate, use the difference in **percentage points**. A refund rate going from 4.0% to 5.0% is +1.0 pts. Calling it +25% is correct arithmetic and misleads almost everyone who reads it.

**Write a file, not a screen.** The script writes `reports/report-<monday>.md`. The file name carries the week, so running it twice for the same week overwrites the same file and running it next week adds a new one. The script prints only the path, so it can run from a scheduler.

## Walk through

Find the last complete week:

```python
from datetime import date, timedelta
last = date(2026, 10, 22)  # a Thursday
sunday = last - timedelta(days=(last.weekday() + 1) % 7)
print(sunday, sunday - timedelta(days=6))
```

This prints `2026-10-18 2026-10-12`: the data stops on a Thursday, so the report covers the week of 12 October.

Percent change and points change:

```python
this_rate, last_rate = 5.0, 4.0
print("%+.1f pts" % (this_rate - last_rate))
print("%+.1f%%" % ((this_rate - last_rate) / last_rate * 100))
```

The first line is what the report shows. The second is the version to avoid.

Run the worked answer:

```
python3 solution/solution.py
```

It writes `reports/report-2026-10-19.md`:

```
| KPI | This week | Last week | Change |
|---|---|---|---|
| Revenue | $19,629.98 | $19,565.07 | +0.3% |
| Paid orders | 143 | 145 | -1.4% |
| Average order value | $137.27 | $134.93 | +1.7% |
| Refund rate | 5.9% | 7.6% | -1.7 pts |
```

Revenue is up a little on fewer paid orders, because each order was worth more. That one sentence is the note for the founders, and the table is the evidence. Pass `--week 2026-10-12` to rebuild an older week.

## Your turn

Open `exercise.py`. Fill in `latest_complete_week`, `rows_in_week`, `compute_kpis`, `pct_change`, `format_change` and `build_report`. The tests read the file your script writes, so match the table layout above line for line. Then run, from this folder:

```
python3 test_lesson.py
```

## Check yourself

1. Why default to the last complete week instead of the last 7 days?
2. Refund rate went from 4.0% to 5.0%. How do you report the change?
3. Last week had 0 paid orders. What goes in the change column, and why not 0%?
4. Why test the function that computes the KPIs separately from the function that writes the file?

<details>
<summary>Answers</summary>

1. Weeks are what people compare. A rolling 7 days starting on a Thursday mixes two weeks, and a partial week compared with a full week looks like a drop.
2. +1.0 percentage points. Percent change on a rate (+25%) is easy to misread as the rate going up by 25 points.
3. `n/a`. Any change from 0 is undefined. Writing 0% claims there was no change, which is false.
4. When a number is wrong you want to know whether the maths or the formatting broke. Small functions with their own tests point straight at the broken step.

</details>

## In real job postings

Automating recurring reports is one of the first places an analyst's Python pays off. On the Real Analyst Jobs live feed read on 25 October 2026, 48% of the 2,102 US analyst postings that list tools ask for Python, and 49% of the 914 such India postings do. See the [Python skills page](https://realanalystjobs.com/skills/python), or check a change by hand with the [percentage change calculator](https://realanalystjobs.com/tools/percentage-change-calculator).

## Next

That ends phase 05. Go on to [06 AI for analysts](../../06-ai-for-analysts/).
