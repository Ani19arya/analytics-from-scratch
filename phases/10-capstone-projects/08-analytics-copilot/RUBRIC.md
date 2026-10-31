# Rubric: capstone 10-08, the Bramblequay copilot

The test checks the numbers and the orchestrator behaviour with one right answer. This rubric scores everything else in [DELIVERABLES.md](DELIVERABLES.md). Score each row 0, 1 or 2. Out of 14: 12 or more is ready for the ops meeting; 8 to 11 needs one more pass; below 8, go back to the analysis table and start the write-up again.

| Area | 0 points | 1 point | 2 points |
|---|---|---|---|
| 1. Framing | Repeats the copilot's draft, or describes the agents instead of answering | Explains the fall but not whether to run the discount, or the other way round | Opens with why weekend rentals fell and a clear no to the discount, with the one or two numbers Odile can quote |
| 2. Data handling | Uses raw rows, or counts false starts | Dedupes and drops false starts, but misses the snapshot, the calendar or the missing station | Clean rentals stated (snapshot, latest load, at least 2 minutes), compares per weekend day (10 against 8 days), and names BQ13 as the reason the zones do not add up |
| 3. The analysis | Blames demand, weather or price with no evidence | Points to Riverside but does not size it, or sizes it from totals | A per-weekend-day bridge that adds up (about 25.6 to 21.4: Riverside -5.8, other zones +0.4, unplaced BQ13 +1.1) and the permutation result outside Riverside in plain words |
| 4. Oversight of the agents | Treats the draft as the answer | Finds some draft problems but not why each matters | Explains each intervention: the S4 edit (Friday is not the weekend), the S5 rejection (emails, and the gateway would block them anyway), the failed reconciliation, and each bad claim (wrong base, a number from a rejected step, an unlabelled 15%) |
| 5. Recommendation | "Monitor the situation" or the discount | An action without an owner, a date or a reason | Specific actions with owners and dates, for example: no discount; confirm Riverside reopened on 1 October and report October weekends per day; add BQ13 to the station list and rerun; keep the approval step and the claim check on every copilot answer |
| 6. Limits | None, or "more data needed" | One real limit | Two or more specific limits and what would change the answer: one month after the closure, 8 weekend days is a small sample, no weather or event data, BQ13 may have taken rides from Riverside users, simulated agent outputs |
| 7. Communication | Longer than a page, or the audit log pasted in as the answer | One page, but numbers in prose disagree with the tables, or jargon with no plain words | One page, every number traceable to the log or the analysis table, the chart per weekend day with a zero baseline and the unit |

## Checks before you send

- Every month-to-month comparison of weekend rentals is per weekend day, or says how many weekend days each month had.
- No number in the write-up comes from a step that did not run.
- You did not ask for or use any rider email address.
- You said what the copilot did well, not only what it did wrong: most of its queries and 11 of its 13 cited numbers were right, and the planned checks caught a real data problem.
