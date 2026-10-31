# Interview rubric and question bank

This file is for the tutor's **Interviewer mode** (see `SKILL.md`). It holds a 45 minute mock analytics interview: the rounds, a 1 to 4 scale with anchors, what would pass and what would not, red flags, follow-up questions, a scorecard template, and a question bank. Every question comes from a live course lesson, named by id and path. Every company and person in it is fictional, from the lessons. All numbers come from the lessons' synthetic data.

A mock built from the course measures practice on the course's own material. It is not a prediction of any real interview, and it is not a promise of a job.

## The rounds

| Round | Time | What it tests |
|---|---|---|
| 1. SQL | about 12 min | Writing a correct query, and spotting the trap that gives a plausible wrong number |
| 2. Statistics | about 10 min | Choosing and reading a test, power, and what can make a result wrong |
| 3. Metrics case | about 12 min | Structure: clarify, check the data, break down, segment, cause, next step |
| 4. Behavioural | about 6 min | A true story with a question, a method, a number and a decision |
| 5. Wrap-up and scorecard | about 5 min | Self-review, then the scorecard |

## The scale

Every round is scored 1 to 4. Score what the candidate said and wrote, not what they might know.

| Score | Label | Anchor |
|---|---|---|
| 4 | Strong | Correct, and found the trap without help. Handled the follow-ups (edge cases, what would make it wrong). Explained it clearly in a sentence a stakeholder could use. |
| 3 | Pass | Correct, or correct after one small self-correction. Found the main trap, perhaps after one follow-up. Explained it well enough. |
| 2 | Not yet | Partly correct. Missed the trap until told, or gave the right number with the wrong reasoning, or needed several nudges. |
| 1 | Below bar | Wrong answer defended as right, no structure, or no attempt. Or a red flag below. |

**Overall result.** Pass the mock when at least three rounds score 3 or more and no round scores 1. Otherwise "not yet": the scorecard names the lessons to revisit. Show every round's score, so the rule can be checked.

**Nudges.** One neutral nudge in a round ("What would you check first?") costs nothing if they then get there. Two or more nudges cap that round at 2. Say on the scorecard how many nudges there were.

## Round 1: SQL

**Criteria.** The query returns the right rows on the given data. The grain of the result is right (one row per what?). They name the trap before or while writing. They handle NULLs, ties, duplicates and empty groups. They say how they would check the result.

**Would pass (3 or 4).** For S1, second highest salary: "I will take the maximum below the maximum, `SELECT MAX(salary) FROM employees WHERE salary < (SELECT MAX(salary) FROM employees)`, not `LIMIT 1 OFFSET 1`, because two people can tie at the top. It gives 175,000 here, and NULL if everyone earns the same."

**Would not pass (1 or 2).** "`ORDER BY salary DESC LIMIT 1 OFFSET 1`." Then, when asked about ties: "There probably are not any." The query returns 182,000, the top salary again, and the candidate does not check.

**Follow-ups to probe with.**

- "What if two people tie for that value?" (ties)
- "What if a value is NULL? What does `COUNT(*)` give against `COUNT(column)`?" (NULLs)
- "What does your query return on an empty table, or when every row is the same?" (edge cases)
- "How many rows do you expect back, and how would you check that?" (grain, fan-out)
- "What changes if this were PostgreSQL instead of SQLite?" (dialects; see `01-14`)

**Red flags.** Hard-coding the answer into the query. Using `RANK` or `ROW_NUMBER` without saying how ties are handled. `WHERE column = NULL`. A join whose row count they never check.

## Round 2: Statistics

**Criteria.** They pick a test that fits the data and say why. They state the null hypothesis and read the p-value correctly. They give the effect size with a range, not only a p-value. They ask about the design: was assignment random, was the split right, was the sample size fixed in advance. They say what would make the result wrong.

**Would pass (3 or 4).** For T1, the Harbor Mealkits checkout test: "Two proportions, so a two-proportion z-test. The new page is ahead by 1.57 points, z is about 1.05 and p is about 0.30. A gap that size is common if the pages were the same, so this test does not show the page works. That is not the same as no effect: I would check power for the lift we care about before dropping it."

**Would not pass (1 or 2).** "p is 0.30, so there is a 70% chance the new page is better." Or: "Not significant, so the page does not work, drop it."

**Follow-ups to probe with.**

- "Why this test and not another?" (why this test)
- "What does the p-value mean, in one sentence?" (interpretation)
- "Was the test big enough to find the lift we care about?" (power)
- "What would make this result wrong?" (SRM, peeking, many metrics, a confounder)
- "We checked the dashboard every day. Does that matter?" (peeking)
- "Give me a range for the effect, not only yes or no." (confidence interval)

**Red flags.** "The p-value is the chance the null is true." Switching to a one-sided test after seeing the result. Reading a group that failed the sample ratio check. "Not significant" reported as "no effect". Computing power from the observed gap.

## Round 3: Metrics case

**Criteria.** They clarify the metric, the period and any launches before touching data. They check the data is real (a second source) before explaining it. They break the metric into parts that multiply or add to it. They segment by a dimension whose members stay the same across the two periods. They name the cause, the step and the segment with numbers. They give a next step and an owner.

**Would pass (3 or 4).** For M1, Lanternway sign-ups: "First, which event is 'sign-ups', which weeks, and did anything launch? A release went out on 19 October, so I check the event count against accounts in the database by app version. They agree, so the drop is real. Visits went up, so it is not traffic. The finish rate fell, and web lost 302 of the 323. On web the finish rate fell from 53.3% to 32.8% from 19 October. The web team should check what changed in the sign-up form that day."

**Would not pass (1 or 2).** "Probably a paid campaign ended, I would look at marketing spend." Or: "Android 5.1 lost 287 sign-ups, so the old Android version broke." (Its users upgraded to 5.2; the segment's membership changed.)

**Follow-ups to probe with.**

- "What is the first thing you would check, and why?" (data before story)
- "How would you know this is not a tracking bug?" (a second source)
- "Why that dimension and not app version?" (segments that hold the same people)
- "This segment fell 50%. How much of the total drop does it explain?" (share of change, not percent)
- "What would you tell the COO in one sentence?" (stakeholder line)
- "What would make your conclusion wrong?"

**Red flags.** Naming a cause before any breakdown. Never checking whether the counting broke. Ranking segments by percent change. Comparing weeks with different weekdays. Inventing numbers the interviewer did not give.

## Round 4: Behavioural

**Criteria.** The story has the shape from `07-11`: Situation, Question, Action, Result, Learned. The Action names one check or trap, not every step. The Result has a number with a comparison and a decision that changed. They say "I" with the right verb. A course or portfolio project is labelled as one. They can trace every number. They have an honest reflection.

**Would pass (3 or 4).** "In a portfolio project on a synthetic subscription dataset, the head of growth believed trial customers cancel faster. I split trial conversion from churn after the first payment. 224 of 779 trial starters, 28.8%, never paid, while the churn gap among paying customers could have been zero. So I recommended work on trial conversion and a test before changing the trial. The comparison was observational, which is why I asked for the test."

**Would not pass (1 or 2).** Four minutes on cleaning and joins and no result. "We did a dashboard and everyone liked it." A course project presented as a job at a company. "I am a perfectionist, I do not make mistakes."

**Follow-ups to probe with.**

- "How did you get that number?" (traceable)
- "What did you do, as opposed to the team?" (ownership)
- "What decision changed because of it?" (impact)
- "What would you do differently?" (reflection)

**Red flags.** A number they cannot explain. Claiming the outcome ("I cut churn") when they measured or recommended. Presenting synthetic course data as a real employer's results.

## Round 5: Wrap-up and scorecard

Ask: "Anything you would change about your answers?" A candidate who finds their own mistake here earns credit in the note for that round, but the score stays on what was said in the round. Then give the scorecard.

## Scorecard template

Fill in one block per round, then the overall result.

```
Mock analytics interview: scorecard
Role aimed at: <data / product / business / BI analyst>
Date: <today>

Round 1, SQL: <score>/4 (<Strong / Pass / Not yet / Below bar>)
  Question: <bank id and short title>, from <lesson id> <lesson path>
  Would pass: <one line from this rubric's pass bar for the question>
  Evidence: "<short quote of what they said or wrote>", "<another quote>"
  Met the bar: <yes / partly / no>, because <one sentence>
  Nudges: <0 / 1 / 2+>
  Revisit: <lesson id> <path>, <lesson id> <path>

Round 2, Statistics: ... (same fields)
Round 3, Metrics case: ... (same fields)
Round 4, Behavioural: ... (same fields)

Overall: <pass / not yet> (rounds at 3 or more: <n> of 4; any round at 1: <yes / no>)
Strongest moment: "<quote>"
Fix first: <one thing, and the lesson for it>
Model answers: <for each round, the answer from the bank entry and its lesson>

This is a practice mock built from the course. It does not predict a real interview or promise an offer.
```

Quote only what the candidate said. If a round was cut short by time, write "not finished" and score what was said.

## Question bank

Each entry has: an id, the source lesson (id and path), the question as the interviewer asks it, the data, what a passing answer contains, and the follow-ups. Run any SQL against a lesson's data from the repo root with `python3 tools/query.py <lesson-path> "<SQL>"`; it loads every `data/*.csv` in that folder as a table.

### SQL

**S1. Second highest salary.** Source: `07-02`, `phases/07-getting-hired/02-sql-interview-questions/`.
Ask: "Fernhill Software has a table `employees(emp_id, name, department, salary)`. Return the second highest salary."
Pass: the maximum below the maximum, 175,000. Says why `LIMIT 1 OFFSET 1` fails (two people share 182,000) and that the query returns NULL when everyone earns the same.
Follow-ups: "What if everyone earns the same?" "Now the third highest?" "Now per department?"

**S2. Duplicate sign-ups.** Source: `07-02`, `phases/07-getting-hired/02-sql-interview-questions/`.
Ask: "`signups(signup_id, email, signed_up_at)`. Which people signed up more than once?"
Pass: `GROUP BY LOWER(TRIM(email)) HAVING COUNT(*) > 1`. 14 people after cleaning against 2 when grouping the raw text. Says why the key needs cleaning.
Follow-ups: "Keep only the first sign-up per person." "What other differences could hide a duplicate?"

**S3. Three day streaks.** Source: `07-02`, `phases/07-getting-hired/02-sql-interview-questions/`.
Ask: "`logins(user_id, login_date)`. Which users logged in on 3 or more consecutive days?"
Pass: distinct user and day first, then day number minus `ROW_NUMBER` as the island key, group and count. 29 users; 34 without `DISTINCT`. Explains why the difference is constant inside a streak.
Follow-ups: "A user logs in twice on one day. What happens without DISTINCT?" "Now the longest streak per user."

**S4. Top two salary levels per department.** Source: `07-02`, `phases/07-getting-hired/02-sql-interview-questions/`.
Ask: "Return the people with the top two salaries in each department."
Pass: asks whether ties count, then uses `DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) <= 2`. In Marketing two people share 182,000, so `DENSE_RANK` returns three people and `RANK` or `ROW_NUMBER` return two.
Follow-ups: "When would you want ROW_NUMBER instead?" "Is ROW_NUMBER's choice between tied rows stable?"

**S5. Month over month with a missing month.** Source: `07-02`, `phases/07-getting-hired/02-sql-interview-questions/`.
Ask: "`orders(order_id, order_date, amount)`. Revenue by month and the change from the previous month."
Pass: builds the full month list (recursive CTE), LEFT JOINs revenue, fills 0, then `LAG`, dividing by `NULLIF(prev, 0)`. Notices April 2026 has no orders, so a plain `LAG` compares May with March (a fake 13.1% fall).
Follow-ups: "What should the change be for the month after a zero month?" "Now a 7 day rolling sum." (the frame changes; see Check yourself 4 in the lesson)

**S6. Running total by day.** Source: `07-02`, `phases/07-getting-hired/02-sql-interview-questions/`.
Ask: "A running total of revenue by day for September 2026."
Pass: aggregate to one row per day first, then `SUM(...) OVER (ORDER BY order_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)`. 20 rows, not 40.
Follow-ups: "What if a day has no orders?" "ROWS or RANGE, and why does it matter here?"

**S7. Customers with no orders, and a report that came out too high.** Source: `01-02`, `phases/01-sql/02-joins-without-losing-rows/`.
Ask: "Brightcart has `customers`, `orders` and `customer_addresses(customer_id, city, is_primary)`. First, list customers who never ordered. Second, revenue by city: last month's version came out higher than the order total. Why?"
Pass: LEFT JOIN and `o.order_id IS NULL`, or `NOT EXISTS`: 28 of 120 customers. Revenue by city must use one address per customer (`is_primary = 1`) and should add up to the order total, 29,551.86. Joining every address double counts customers with two addresses (8,847.68 too high).
Follow-ups: "`NOT IN (SELECT customer_id FROM orders)` returns no rows. Why might that be?" (a NULL in the subquery) "You add `WHERE o.amount > 50` after the LEFT JOIN. What happens?" "How do you check a join did not fan out?"

**S8. Missing delivery dates and the average tip.** Source: `00-05`, `phases/00-start-here/05-nulls-case-and-coalesce/`.
Ask (a short warm-up): "Tiffinbell `orders(order_id, order_date, city, status, amount, delivered_date, tip)`. How many orders have no delivery date, and what is the average tip?"
Pass: `delivered_date IS NULL`, not `= NULL`: 34 orders, split by status (cancelled and in transit are expected; delivered without a date is a bug). Asks what an empty tip means before averaging: 18.79 over the 132 recorded tips, against 12.16 if missing tips are counted as 0.
Follow-ups: "`COUNT(*)` against `COUNT(tip)`?" "When is `COALESCE(tip, 0)` right?" "Where does a NULL go in a CASE expression?"

### Statistics

**T1. Did the new checkout page work?** Source: `07-09`, `phases/07-getting-hired/09-statistics-interview-round/`.
Ask: "Harbor Mealkits tested a new checkout page for two weeks. Control: 74 orders from 798 visitors. Treatment: 87 from 802. Did it work?"
Pass: two-proportion z-test; 9.3% against 10.8%, a gap of 1.57 points, z about 1.05, p about 0.295. "This test does not show it works", not "it does not work". Gives the p-value's meaning correctly.
Follow-ups: "So there is a 70% chance the page is better?" (no) "Was the test big enough?" (leads to T2) "What does a confidence interval add?"

**T2. Was the test big enough?** Source: `07-09`, `phases/07-getting-hired/09-statistics-interview-round/`; the formula is from `02-04`, `phases/02-statistics-and-experiments/04-sample-size-before-you-test/`.
Ask: "The lift that matters to Harbor Mealkits is 1.5 points on a 9.3% baseline. Was 800 per group enough?"
Pass: power for the lift that matters, not the observed gap: about 17%. About 6,291 users per group for 80% power. So "not significant" here means "too small to tell", and the next step is a bigger test.
Follow-ups: "Why not compute power at the 1.57 points you saw?" "What happens to n if you want 90% power?" "To halve the margin of error, how many more users?" (about four times)

**T3. Coupons and reorders.** Source: `07-09`, `phases/07-getting-hired/09-statistics-interview-round/`; the idea is from `02-10`, `phases/02-statistics-and-experiments/10-correlation-causation-and-simpson/`.
Ask: "Customers who got a coupon reordered less than those who did not: 37.0% against 50.4%. Should we stop sending coupons?"
Pass: asks how coupons were given out and splits by customer type. New: 31.1% with a coupon against 18.5% without; returning: 67.7% against 62.7%. The total reverses because most coupons went to new customers, who reorder less anyway. Coupons were not random, so a randomised coupon test is the clean answer.
Follow-ups: "Which comparison answers 'does a coupon help a new customer?'" "When is the total the right number?"

**T4. Ship the shorter checkout?** Source: `02-03`, `phases/02-statistics-and-experiments/03-ab-test-from-scratch/`.
Ask: "Tidewater Outdoor split 1,900 visitors between the current checkout (A) and a shorter one (B). A: 10.96% of 976. B: 14.6% of 924. Dana wants to ship B on Thursday. What do you check, and what do you tell her?"
Pass: checks the split first (sample ratio check; 976 against 924 is within chance for a planned 50/50). Lift 3.65 points, p about 0.017, 95% interval about 0.6 to 6.7 points. Recommends shipping and planning on a modest gain. Says points, not "33%" without saying it is relative.
Follow-ups: "B is ahead, so can we use a one-sided test?" (not after looking) "What if the split had been 976 against 824?" (SRM, stop and find the bug) "The lift is significant but 0.1 points. Ship?"

**T5. Five variants, three metrics.** Source: `02-13`, `phases/02-statistics-and-experiments/13-ab-test-pitfalls/`.
Ask: "Brindlefox tested the recipe page against four challengers on three metrics, 20% of users each. The slide says E won signups by 2.3 points with p = 0.0009, and on day 7 someone posted that C was winning. What do you ship?"
Pass: sample ratio check across all five groups first; E has about 380 fewer users than planned, so its result cannot be read, whatever its p-value. Twelve comparisons need an adjustment (Holm to decide what to ship). C's day 7 result is a peek. Ships B (about 4.5 points on signups, Holm-adjusted p below 0.001) and expects the real lift to be smaller.
Follow-ups: "E's p-value is tiny. Why not report it with a caveat?" "Holm or Benjamini-Hochberg, and when?" "We only peeked, we did not stop early. Fine?"

**T6. True or false.** Source: `07-09`, `phases/07-getting-hired/09-statistics-interview-round/` and `02-03`, `phases/02-statistics-and-experiments/03-ab-test-from-scratch/`.
Read one or two statements and ask "true or false, and why?":

- "p = 0.30 means a 30% chance the new page makes no difference." False: the p-value assumes no difference.
- "To halve the margin of error you need about four times as many users." True: the margin shrinks with the square root of n.
- "Checking the p-value every day and stopping when it dips below 0.05 keeps the false positive rate at 5%." False: in the lesson's simulation it reaches about 20%.
- "A tiny p-value means a big effect." False: it measures surprise, not size.

### Metrics case

**M1. Sign-ups fell 20%.** Source: `07-08`, `phases/07-getting-hired/08-metrics-case-interview/`.
Open with: "I am Grace, analytics lead at Lanternway Courses. Sign-ups fell 20% last week. Walk me through it."
Reveal on request: sign-ups mean the "signup completed" event; weeks are 12 to 18 against 19 to 25 October; new iOS (4.9) and Android (5.2) releases on 19 October. Totals: visits 21,622 to 21,706, starts 2,980 to 2,943, sign-ups 1,666 to 1,343 (minus 19.4%). Events against database accounts: 97% to 99% on every app version (the tracker is fine). By platform: web 795 to 493, iOS 441 to 424, Android 430 to 426. Web finish rate 53.3% to 32.8%; web visits and start rate flat.
Pass: the order of `07-08` (clarify, check the data, break down, segment, cause, next step). Names web and the finish rate, with numbers, and the web team as owner.
Follow-ups: "Android 5.1 lost 287 sign-ups. Is that a finding?" "We cannot get the accounts table. How else would you test for a tracking bug?" "Visits went up. What does that rule out, and what not?"

**M2. DAU fell 20% overnight.** Source: `03-10`, `phases/03-metrics-and-product-analytics/10-diagnose-a-metric-drop/`.
Open with: "I am Meera, COO at Tiffinbell. Thursday's DAU was 1,299 against 1,635 the Thursday before, down 20.6%. I have an investor call at 4 pm. Did people stop using the app?"
Reveal on request: the mobile team shipped app version 7.4 this week. Backend server users: 1,698 on Thursday, the same as the Thursday before. By platform: Android DAU minus 39.5% while Android server users rose 4.2%; iOS and web roughly flat. Android 7.4 reports about 7% of its users to analytics; every other version about 96%.
Pass: same weekday comparison and calendar first; then a second source (server users) before any segment story; calls it a tracking bug in Android 7.4; corrected DAU about 1,646; says what to tell Meera and that the dashboard should be annotated, not overwritten.
Follow-ups: "Android DAU fell 40%. Why is 'Android users are leaving' wrong?" "Every city shows a drop. Does that rule out a city cause?" "The bug is fixed on 26 October. What do you do with the dashboard for 21 to 25 October?"

**M3. Conversion up 2% or down?** Source: `03-06`, `phases/03-metrics-and-product-analytics/06-percent-points-and-averages-of-ratios/`.
Open with: "I am Asha, CEO of Learnhaven. Marketing says conversion is up 2% in October. Finance says it fell from 2.37% to 1.92%. Which is right?"
Reveal on request: an October campaign brought 40.8% of the month's visits and converted at under 1%. Ordinary days rose from 2.37% to 2.60%. Total orders rose 25%. Marketing averaged the daily rates.
Pass: separates points from percent; explains ratio of sums against average of ratios; gives one honest sentence: down overall (minus 0.45 points) because of the campaign's mix, up on ordinary days.
Follow-ups: "Conversion went from 4% to 5%. Say the change two ways." "When is the average of ratios the right number?"

**M4. Launch quick apply?** Source: `03-04`, `phases/03-metrics-and-product-analytics/04-north-star-and-guardrails/`.
Open with: "I am Lena, product director at Jobnest. Our quick apply test shows more people applying. Can I launch on Monday?"
Reveal on request: 1,800 job seekers, randomised, two weeks. Share applying: 30.3% to 36.6% (plus 6.3 points, 95% interval plus 1.95 to plus 10.6). Employer reply rate: 20.2% to 13.1%; even the favourable end of its interval is a 3.5 point drop. The rule agreed before the test: reply rate may fall at most 2 points, unsubscribes may rise at most 0.5 points. Unsubscribes went from 21 to 16, minus 0.61 points with an interval of minus 1.92 to plus 0.71.
Pass: asks for the guardrails and the launch rule written before the test; uses intervals, not raw changes; does not launch, because the reply rate breaches its 2 point limit; adds that the unsubscribe guardrail cannot rule out a rise above 0.5 points because the test was too small for it; if the business ships anyway, it is a named trade, not a moved threshold.
Follow-ups: "The north star rose 6 points and a guardrail fell 7. The CEO says ship. What do you say?" "Suggest a north star that would not reward spam applications."

### Behavioural

The candidate answers from their own experience or a course project, labelled honestly. Score on the shape in `07-11`, `phases/07-getting-hired/11-behavioural-answers/`, not on how impressive the story is.

**B1.** "Tell me about a time your analysis changed a decision." Source: `07-11`. Pass: a decision before and after, and the number that moved it.

**B2.** "Tell me about a time you explained a technical result to a senior person." Source: `07-11`; also `07-06`, `phases/07-getting-hired/06-explain-findings-to-leadership/`. Pass: answer first, a specific before and after, a number stated with its range.

**B3.** "Tell me about a mistake you made." Source: `07-11`. Pass: a real mistake, the check that found it, its size, and the habit it changed. "I do not make mistakes" fails.

**B4.** "Tell me about a time the data was not what you expected." Source: `07-11`; also `07-10`, `phases/07-getting-hired/10-the-take-home-assignment/` (duplicates, test orders, refunds, each with a count). Pass: what they found, the count, and what they did about it.

**B5.** "Tell me about a time you disagreed with a stakeholder." Source: `07-11`. Pass: the stakeholder's belief, the evidence, what they recommended, and how it ended, told without blame.

## Lessons to revisit, by round

Use these on the scorecard. All are live lessons in `curriculum.json`.

| Round | Weak spot | Revisit |
|---|---|---|
| SQL | Ties, top N, streaks, month over month | `07-02` `phases/07-getting-hired/02-sql-interview-questions/`, `01-03` `phases/01-sql/03-window-functions/`, `01-11` `phases/01-sql/11-gaps-and-islands/` |
| SQL | Joins dropping or duplicating rows | `01-02` `phases/01-sql/02-joins-without-losing-rows/`, `01-06` `phases/01-sql/06-anti-joins-self-joins-and-union/` |
| SQL | NULLs | `00-05` `phases/00-start-here/05-nulls-case-and-coalesce/` |
| SQL | Duplicates and checking totals | `01-08` `phases/01-sql/08-duplicates-and-reconciliation/` |
| Statistics | The z-test, p-values, intervals, SRM | `02-03` `phases/02-statistics-and-experiments/03-ab-test-from-scratch/`, `02-02` `phases/02-statistics-and-experiments/02-confidence-interval-by-hand/` |
| Statistics | Power and sample size | `02-04` `phases/02-statistics-and-experiments/04-sample-size-before-you-test/`, `07-09` `phases/07-getting-hired/09-statistics-interview-round/` |
| Statistics | Many metrics, peeking, broken splits | `02-13` `phases/02-statistics-and-experiments/13-ab-test-pitfalls/` |
| Statistics | Confounders and Simpson's paradox | `02-10` `phases/02-statistics-and-experiments/10-correlation-causation-and-simpson/` |
| Metrics case | Structure of the case | `07-08` `phases/07-getting-hired/08-metrics-case-interview/`, `03-10` `phases/03-metrics-and-product-analytics/10-diagnose-a-metric-drop/` |
| Metrics case | Breaking a metric into parts | `03-01` `phases/03-metrics-and-product-analytics/01-metric-trees/`, `03-02` `phases/03-metrics-and-product-analytics/02-funnel-conversion/` |
| Metrics case | Segments and mix | `03-09` `phases/03-metrics-and-product-analytics/09-segmentation-and-mix-effects/`, `03-06` `phases/03-metrics-and-product-analytics/06-percent-points-and-averages-of-ratios/` |
| Metrics case | Launch rules and guardrails | `03-04` `phases/03-metrics-and-product-analytics/04-north-star-and-guardrails/` |
| Behavioural | Story shape and true numbers | `07-11` `phases/07-getting-hired/11-behavioural-answers/`, `07-07` `phases/07-getting-hired/07-resume-bullets-that-are-true/` |
| Behavioural | Leading with the answer | `07-06` `phases/07-getting-hired/06-explain-findings-to-leadership/` |
