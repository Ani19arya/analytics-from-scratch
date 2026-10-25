# Dates, weeks and time zones

How many people signed up each week over the new year, counted on the clock the team actually works on?

## The problem

Tidewell, a fictional budgeting app, logs every sign-up with a UTC timestamp. Meera, the growth lead in Bengaluru, wants weekly sign-ups with week-over-week change for her January review, counted in India time. Sam, who runs the US team, wants the same report in Pacific time. Last year the spreadsheet version broke in the first week of January and showed a week called W00. You need one piece of code that buckets any timestamp correctly in any of the three zones and never breaks at a year end.

The file `data/signups.csv` (700 events, 8 December 2025 to 18 January 2026, UTC) is synthetic, built by `make_data.py` with a fixed random seed.

## What you will build from scratch

- `to_zone`: shows a UTC instant on the IST or PST clock.
- `iso_week_key`: labels any date with its ISO week, such as `2026-W01`.
- `count_by`: counts events by day, week or month in a chosen zone.
- `previous_week` and `week_over_week`: a weekly table with the change from the week before, correct across the year end.

## The idea

**A timestamp is an instant. A day is a local idea.** `2025-12-31T20:00:00Z` is 31 December in London, 1 January in India (UTC+5:30, so 01:30) and still 31 December in California (UTC-8, so 12:00). Which day an event belongs to depends on whose calendar you use. Pick the zone of the people reading the report, convert first, then bucket. Never bucket in UTC and then relabel.

In this data the choice changes the numbers. On 1 January there were 20 sign-ups by the UTC day, 19 by the IST day and 24 by the PST day.

**ISO weeks.** An ISO week runs Monday to Sunday. Week 1 is the week that contains the year's first Thursday. So a week can start in one calendar year and belong to the next ISO year:

```
Mon 29 Dec 2025 .. Sun 4 Jan 2026  ->  2026-W01
```

Wednesday 31 December 2025 is in `2026-W01`. If you label it with the calendar year (2025) and the ISO week number (1), you get `2025-W01`, a week that happened twelve months earlier. Always take the year and the week from the same `isocalendar()` call.

The `%W` code in `strftime` is not ISO. It counts Mondays from 1 January and puts the days before the first Monday into week 00. It splits the new-year week in two.

**Previous week by dates, not by numbers.** Week 1 minus 1 is not week 0. Take the Monday of the week, subtract 7 days, and label that date. This also handles years with 53 ISO weeks, such as 2020.

**Week-over-week change** is

```
change % = (this week - last week) / last week * 100
```

It is undefined when last week is 0, so return nothing instead of dividing by zero. Weeks with no events must still appear, as 0, or the next week gets compared with the wrong week.

## Walk through

See the `%W` trap:

```python
from datetime import date
for d in [date(2025, 12, 31), date(2026, 1, 1)]:
    print(d, d.strftime("%Y-W%W"), d.isocalendar()[:2])
```

The `%W` labels are `2025-W52` and `2026-W00`, two weeks for days that are two days apart. The ISO labels are `(2026, 1)` for both.

Convert one instant to three clocks:

```python
from datetime import datetime, timedelta, timezone
ts = datetime(2025, 12, 31, 20, 0, tzinfo=timezone.utc)
for name, hours in [("UTC", 0), ("IST", 5.5), ("PST", -8)]:
    print(name, ts.astimezone(timezone(timedelta(hours=hours))).strftime("%Y-%m-%d %H:%M"))
```

Find the previous week with date arithmetic:

```python
from datetime import date, timedelta
monday = date.fromisocalendar(2026, 1, 1)
y, w, _ = (monday - timedelta(days=7)).isocalendar()
print("%d-W%02d" % (y, w))
```

This prints `2025-W52`.

Run the worked answer:

```
python3 solution/solution.py
```

It prints daily and monthly counts in all three zones, then the IST weekly table. Look at the last row: `2026-W04` has 4 sign-ups and a change of -96.4%. The data ends on Sunday 18 January in UTC, and in IST the last hours of that Sunday are already Monday. That week has only a few hours of data. A partial week compared with a full one is the most common false alarm in weekly reporting. Cut the report at the last complete week in the reader's zone.

## Your turn

Open `exercise.py`. Fill in `to_zone`, `iso_week_key`, `count_by`, `previous_week` and `week_over_week`. Then run, from this folder:

```
python3 test_lesson.py
```

## Check yourself

1. Which ISO week is 31 December 2025 in, and why?
2. Your events are stored in UTC and the report is for a team in India. In what order do you convert and bucket?
3. Why must a week with zero events still appear in the weekly table?
4. This week shows a 96% drop. What is the first thing you check?

<details>
<summary>Answers</summary>

1. `2026-W01`. ISO week 1 is the week containing the first Thursday of the year. 1 January 2026 is a Thursday, so the week from Monday 29 December 2025 is week 1 of 2026.
2. Convert each timestamp to IST first, then take the day, week or month. Bucketing in UTC puts events from 00:00 to 05:30 IST on the wrong day.
3. Otherwise the week after it is compared with the last week that had data, which might be two weeks back, and the change is wrong.
4. Whether the week is complete. A week that has just started, or that the data cuts off part way, looks like a collapse.

</details>

## In real job postings

Dates are where analyst Python and SQL both go wrong first. On the Real Analyst Jobs live feed read on 25 October 2026, 70% of the 914 India analyst postings that list tools ask for SQL and 49% ask for Python. See the [Python skills page](https://realanalystjobs.com/skills/python) and the [US analyst job market report](https://realanalystjobs.com/research/us-analyst-job-market-october-2026).

## Next

[04 Automate the weekly report](../04-automate-the-weekly-report/)
