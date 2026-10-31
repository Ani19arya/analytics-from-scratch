# Rubric: capstone 10-04, the Shiftwren churn model

The test checks the numbers with one right answer. This rubric scores everything else in [DELIVERABLES.md](DELIVERABLES.md). Score each row 0, 1 or 2. Out of 14: 12 or more is ready to send to Ciara; 8 to 11 needs one more pass; below 8, go back to the reconciliation and start the memo again.

| Area | 0 points | 1 point | 2 points |
|---|---|---|---|
| 1. Framing | Describes the tables, or opens with method | Answers "is MRR falling" but not which rates to plan with, or the reverse | Opens with the answers to Ciara's four questions, in her order, one sentence each |
| 2. Data handling | MRR summed from raw `amount`, or cleaning not described | Cleaning done but not reconciled, or one of duplicates (with corrections), ids, the definition change or late rows missed | A reconciliation from the reported September MRR to the restated one, one row per fix with the amount it moved, and the reason the reported line fell after April |
| 3. The churn model | One blended rate, or churned / all customers | Rates by plan, but annual customers mixed into a monthly hazard, or no counts behind the rates | Monthly hazard by plan for monthly billing, a renewal rate for annual contracts, expansion separate; each with its counts and window; notes that pro and business cannot be told apart yet |
| 4. Verification | Forecast shown with no test on the past | A backtest is run but its bias is not explained, or a single error number with no direction | Backtest from March with the error by month, the churn-only and expansion versions compared, and the direction of the remaining bias named (reactivations left out, so the forecast is low) |
| 5. Recommendation | "Reduce churn", "improve retention" | An action with no owner or date, or several unranked | One or two actions, each with an owner and a date: finance adopts the restated MRR from the November close; customer success works the January to March 2027 renewals from November |
| 6. Limits | None, or "more data needed" | One real limit | Two or more specific limits with what would change the answer: 50 renewals, mostly non-promotion customers; pro hazard unstable between windows; pending cancels and reactivations not modelled; the definition fix assumed for every old annual row |
| 7. Communication | Longer than a page, or numbers in prose that disagree with the tables | One page, but the chart mixes forecast and actuals without marking them, or the axis does not start at zero | One page, every number traceable to a table, the chart marks the forecast and starts at zero, and the memo says EUR a month every time |

## Checks before you send

- You compared restated with reported and said which one the board should see.
- No hazard includes annual customers, and no renewal rate includes monthly ones.
- The forecast is labelled "existing book, no new sales".
- You named January 2027 and why.
- Nothing claims a cause the data cannot show: the data says who leaves, not why.
