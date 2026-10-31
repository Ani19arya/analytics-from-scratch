# Rubric: capstone 10-03, Brambletoe budget

The test checks the numbers with one right answer. This rubric scores everything else in [DELIVERABLES.md](DELIVERABLES.md). Score each row 0, 1 or 2. Out of 14: 12 or more is ready for the budget meeting; 8 to 11 needs one more pass; below 8, go back to the test readout and start the write-up again.

| Area | 0 points | 1 point | 2 points |
|---|---|---|---|
| 1. Framing | Compares attribution models with no budget answer | A budget answer without the reason the agency's split is wrong, or the reverse | Opens with the split and its expected effect, then answers Sana's "why should we trust it" |
| 2. Data handling | Uses stored display spend, duplicate pixel fires, or touches after the order | Most cleaning done, one step missed or not stated | Every step stated with what it changed: fee added to early display weeks, duplicate weeks and orders removed, Q3 by order time, post-purchase and old touches outside the window |
| 3. Attribution judgement | Picks the model with the answer they like | Shows the four models but treats one as the truth | Explains that every model shares credit among touches and none measures what would have happened without the ad; uses the spread as a warning and the holdout as the evidence |
| 4. Test readout | Ignores the test, or reads "display drove 16 orders" as proof | Reads the lift but not its interval | Lift, interval (which includes zero here) and calibration factor; says the test is too small to be precise, and that it still puts display's incremental orders well below its credit |
| 5. Budget and optimisation | Moves money by gut feel, or the unconstrained optimum with no caveat | Uses the optimiser but does not explain equal marginal cost or the curve assumption | Explains the split by marginal cost per extra order, keeps Daniel's 50% limit, reports the small predicted gain honestly, and names the extrapolation risk |
| 6. Next quarter's measurement | None | "Run more tests" | A specific test with owner and date: for example a longer or larger display holdout in Q4, and a first holdout for paid search on brand terms, sized so the interval excludes zero |
| 7. Limits and communication | No limits; longer than a page | One limit; or the chart has no zero baseline | Two or more specific limits (the curve shape is assumed, search and social are not calibrated, brand search likely over-credited, one test in one month, no revenue or margin); one page; one chart that supports the decision |

## Checks before you send

- Every spend number includes the agency fee.
- The proposal spends the same total budget and stays within 50% of Q3 per channel.
- You never say a model "proves" what a channel caused. Only the holdout measures that, and only for display.
