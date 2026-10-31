# Deliverables: what to hand in

Part of capstone [10-02](README.md). Read [BRIEF.md](BRIEF.md) first.

## 1. The numbers with one right answer (checked by the test)

Fill in every function in `exercise.py`, then run `python3 test_lesson.py` from this folder. The test checks your functions on the committed data, on a second dataset built from another seed, and on small hand-made tables. Use these definitions; the test uses them too.

| Term | Definition |
|---|---|
| User | One per `user_id` with `account_type` = `customer` |
| Cohort | The calendar month of `signup_date` |
| Active in a month | At least one row for that user and month with `lessons_completed` >= 1. Months before the sign-up month and after the last complete month (September 2026) do not count |
| Month k of a cohort | The calendar month k months after the cohort month; month 0 is the sign-up month |
| Retention at month k | Users of the cohort active in month k / cohort size (classic retention: active in that month, whatever happened before) |
| Observed | A cohort is observed at month k only if month k is on or before September 2026. A month that has not happened is missing from the cohort's list, not 0% |
| Pooled curve at k | Sum of active users at k / sum of cohort sizes, over the cohorts observed at k |
| Users lost at month k | Cohort size x (pooled month-k retention of all the OTHER cohorts observed at k - the cohort's month-k retention). Positive means the cohort lost more users than the others would have |
| Two-proportion z-test | z = (p1 - p2) / sqrt(p (1 - p) (1/n1 + 1/n2)) with p the pooled proportion; two-sided p-value = erfc(abs(z) / sqrt(2)) |

## 2. The cohort table

The retention matrix: one row per cohort (January to August 2026), its size, and retention at months 0, 1, 2 and on, blank where not yet observed. Add the pooled curve as the last row.

## 3. Where it breaks, and who

- The month after sign-up where the pooled curve falls the most, with the numbers.
- The cohorts ranked by users lost at month 1, and the one you would hand to the product team first.
- For that cohort: month-1 retention against the other cohorts, with the z-test, and split by `source` and by `platform`.
- Your answer on the June redesign, with the evidence.

## 4. One chart

Retention curves (months since sign-up on the x axis, retention from 0% to 100% on the y axis) that make your main finding visible. Label the lines, say the data is synthetic, and say which cohorts each point pools.

## 5. A one-page write-up for Lucia

At most one page:

1. The answer in two sentences: where retention breaks, for whom, with numbers.
2. The cohort to study first, why that one, and how sure you are.
3. The June question: what the dashboard's cliff really is.
4. What to do: one recommendation for product and one for the holiday campaign, each with an owner, a date, and the expected effect with its assumptions.
5. Limits and what would change your answer.

Score it with [RUBRIC.md](RUBRIC.md). Then read [solution/WRITEUP.md](solution/WRITEUP.md) and compare.
