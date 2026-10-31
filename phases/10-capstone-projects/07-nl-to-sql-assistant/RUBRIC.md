# Rubric: capstone 10-07, the Copperwren question box

The test checks the numbers with one right answer. This rubric scores everything else in [DELIVERABLES.md](DELIVERABLES.md). Score each row 0, 1 or 2. Out of 14: 12 or more is ready to send to Morven; 8 to 11 needs one more pass; below 8, go back to your error analysis and start the write-up again.

| Area | 0 points | 1 point | 2 points |
|---|---|---|---|
| 1. Framing | Describes the prompts and the model, not the decision | Gives accuracy but not the decision, or the decision without the rule behind it | Opens with the decision from the agreed rule (roll out, pilot or hold), v2's accuracy and interval, and the one condition that decided it |
| 2. Data handling | Trusted answers computed on raw rows, or the snapshot rule not stated | Duplicates handled, but the fee change, the late rows or the latest-load rule missed or not explained | States the snapshot (loaded before 1 October, latest load wins) and the fee change, and shows how much each moves one number (for example March revenue 7,430.06 raw against 6,932.27 clean) |
| 3. Evaluation method | Counts a query that ran as a correct answer, or reads the SQL by eye | Compares results with trusted answers, but on one dataset only, or scores clarifications on ambiguous questions as failures | Compares results with tolerance and the column and row-order rules, scores each category on its own terms, notes that some mistakes are right by luck on this data (a BETWEEN date bound in a 30-day month) |
| 4. Safety | "The model refused" is the safety argument | Lists what the gateway blocks but not why it holds if the model or the text checks are fooled | Shows the walls (one statement, read-only file, authorizer allowlist, row cap, time limit), the COUNT(*) gap and its fix, and says safety does not depend on the prompt |
| 5. Statistics | A point accuracy with no interval, or two separate intervals compared by eye | Wilson interval for each version, but no paired test, or the test on all 42 questions | Wilson intervals and the exact McNemar test on the 30 answerable questions, with a sentence on what the interval width means for 30 questions |
| 6. Recommendation and limits | None, or "keep improving the model" | A decision with one generic limit | The decision with owners and dates (for example: roll out v2 behind the gateway; data team adds a "show the SQL" button; re-run this test set on every prompt or model change), and two specific limits: 30 questions, simulated replies, questions written by the team rather than by managers |
| 7. Communication | Longer than a page, or jargon (McNemar, Wilson) with no plain words | One page, but the wrong-number risk is buried or the chart has no interval | One page, the wrong-number risk stated in plain words with a count, every number traceable to the scorecard, chart with intervals and the 0.70 bar |

## Checks before you send

- Every accuracy you quote says "out of 30 answerable questions", not out of 42 or 84.
- The decision follows the rule in BRIEF.md, and you say which condition decided it.
- You did not credit the model for safety: a blocked hostile query is the gateway working, and it would have been blocked with any prompt.
- Nothing claims the assistant is right on questions unlike the test set.
