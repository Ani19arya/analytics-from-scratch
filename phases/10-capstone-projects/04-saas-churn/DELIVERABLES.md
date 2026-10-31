# Deliverables: what to hand in

Part of capstone [10-04](README.md). Read [BRIEF.md](BRIEF.md) first.

## 1. The numbers with one right answer (checked by the test)

Fill in every function in `exercise.py`, then run `python3 test_lesson.py` from this folder. The test checks your functions on the committed data, on a second dataset built from another seed, and on small hand-made event logs. It also checks your forecast against a seeded simulation of the same customers. Use these definitions; they are the ones Declan will rebuild, and the test uses them too.

| Term | Definition |
|---|---|
| Clean event | One row per `event_id`: the load with the latest `loaded_on` (ties: the later row in the file). With an as-at date, only loads on or before it count |
| Account id | Trimmed and upper-cased. Accounts: one row per id, the first one kept |
| MRR of an event | `amount` in EUR a month. Annual-billing events requested before 2026-04-01 are divided by 12; every other amount is already monthly |
| MRR at a month end | For each account, the MRR of its latest clean event with `effective_on` on or before the last day of the month (ties broken by `event_id`). Paying means MRR above 0 |
| MRR bridge of a month | Start = MRR at the end of the previous month, end = at the end of this month, per account: new (paid 0, never paid at an earlier month end), reactivation (paid 0, paid at some earlier month end), expansion, contraction, churn (paid, now 0). Start + new + reactivation + expansion - contraction - churn = end |
| Logo churn | Accounts that churned in the bridge / accounts paying at the start x 100 |
| GRR, NRR (12 months) | Base: accounts paying 12 month ends ago, at that MRR. NRR = their MRR now / base. GRR = sum of min(now, then) / base. Both in % |
| Monthly hazard | Monthly-billing accounts only, by plan at the start of the month: churned / at risk, summed over the 6 months to the base month. Pooled: all plans together |
| Renewal rate | Annual-billing accounts paying at the start of a month in which a whole number of years since their latest start or reactivation is completed: renewed / due, over the 12 months to the base month |
| Expansion rate | Over the 6 months to the base month, for accounts paying at both ends of a month: sum of MRR change / sum of MRR at the start of the month |
| Forecast | For the accounts paying at the end of the base month: monthly accounts x (1 - hazard of their plan) ^ k, annual accounts at full MRR until their next anniversary and x renewal rate from then, all x (1 + expansion rate) ^ k. No new sales, no reactivations |
| Backtest | The same forecast made from March 2026, compared with what those same accounts actually paid at each month end from April to September |
| Reconciliation | Reported (from `finance_close.csv`) = as at close (rows loaded by the 3rd of the next month, no definition fix); then the definition fix; then the late rows; = restated |

## 2. The MRR restatement

A table, one row per month from January 2025 to September 2026: MRR as reported, MRR restated, and the gap. Under it, the September reconciliation in four rows (as at close, definition fix, late rows, restated) so Ciara can see what moved her number and by how much. Answer her first question in one sentence under the table.

## 3. The churn model, as Declan will use it

One small table: monthly hazard for starter, pro and business on monthly billing, the annual renewal rate, the monthly expansion rate, each with the counts behind it (at risk and churned, due and renewed) and the window it was measured on. Then the 6-month forecast of the September book, month by month, and the backtest from March: forecast, actual, error %. Say which version of the model you recommend (churn only or with expansion) and why, using the backtest.

## 4. One chart

Restated MRR at each month end from January 2025 to September 2026, and the forecast from October 2026 to March 2027, marked so nobody mistakes the forecast for actuals. Axis from zero, unit in the title, a note that the data is synthetic. Any tool. `solution/solution.py` draws one in about 30 lines of standard-library SVG; read it after you try your own.

## 5. A one-page memo for Ciara

At most one page, in this order:

1. The answer to "is MRR falling?" in two sentences, with the restated number.
2. The churn rates to plan with, and why one blended 3% is wrong (say which customers it overstates and which it understates).
3. The forecast through March 2027 and the one month Declan must not miss.
4. How far to trust it: the backtest error, and which way it is biased.
5. One recommendation with an owner and a date (for example, about the reported MRR, or about the January renewals), and the limits: what the model leaves out and what would change it.

Score it with [RUBRIC.md](RUBRIC.md). Then read [solution/WRITEUP.md](solution/WRITEUP.md) and compare.
