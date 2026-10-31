# Deliverables: what to hand in

Part of capstone [10-08](README.md). Read [BRIEF.md](BRIEF.md) first.

## 1. The numbers and the behaviour with one right answer (checked by the test)

Fill in every function in `exercise.py` that raises `NotImplementedError`, then run `python3 test_lesson.py` from this folder. The test checks your functions on the committed data, on a second city built from another seed, and on hand-made cases. Use these definitions; the test uses them too.

| Term | Definition |
|---|---|
| Clean rental | One row per `rental_id`: loads before `2026-10-01 00:00:00` only, the latest load wins, and `duration_min` at least 2 |
| Valid plan | Unique step ids; kind `query` (with SQL), `check` (`reconcile` or `noise`) or `recommend`; every dependency is an earlier step. Otherwise `ValueError` |
| Step status | `done`, `rejected`, `skipped` (a dependency is not done), `blocked` (the gateway refused), `failed` (any other query failure), `halted` (no valid approval, or the step budget is used up), `not_reached` (after a halt) |
| Valid approval | The last record for the step, with decision `approve`, `reject`, or `edit` with non-empty `edited_sql`. Anything else halts |
| Audit log | One entry per plan step, in plan order: step, status, detail, and the SHA-256 of the SQL that ran (empty if none) |
| Reconcile | For August and September: sum of S2's zone rows minus S1's total. Passes only if both are 0 |
| Noise check | Daily weekend rentals outside Riverside (S4), August against September: means, and the exact two-sided permutation p-value for the difference in means |
| Claim verdict | `ok` if the cited value equals the claim at the precision written (within 0.5 x 10^-d for d decimals), `mismatch`, `not_run` (the cited step is not done), `no_such_row` (the `where` does not pick exactly one row), `assumption` (labelled, not checked) |
| Uncited number | A number in the draft's text that is not the text of any claim |
| Released | Every check step done and passed, every claim `ok` or `assumption`, no uncited number |

## 2. The audit log

The log of the replayed session as a table: step, agent, what it was for, the decision and who made it, status, SQL fingerprint (first 10 characters is enough). Under it, one sentence per step that did not simply run as planned (an edit, a rejection, a failed check), saying what happened and why it matters.

## 3. The claim check

Every number in the draft, with its cited step, the value you found there, and its verdict. For each problem, the corrected number or the reason it cannot be used.

## 4. The analysis behind the answer

A short table that explains the change in weekend rentals from August to September per weekend day, in parts that add up: Riverside, the other zones, and the rentals the zone breakdown could not place. Say what the calendar alone explains. State the permutation test result for the zones outside Riverside in plain words.

## 5. One chart

Weekend rentals per weekend day, August against September, split into Riverside, the other zones and unplaced rentals (a stacked or grouped bar), with a title that says the unit and a note that the data is synthetic. Any tool.

## 6. A one-page write-up for Odile

At most one page, in this order:

1. The answer in two sentences: why weekend rentals fell, with the numbers she can quote.
2. What you would do, and what you would not do (the discount), each with an owner and a date.
3. What the copilot got right and wrong, and what stopped its mistakes reaching her.
4. Limits: what this data cannot tell you and what would change your answer.

Score it with [RUBRIC.md](RUBRIC.md). Then read [solution/WRITEUP.md](solution/WRITEUP.md) and compare.

## Optional: run the agents against a real model

`live_run.py` sends the planner and recommender prompts to a model of your choice, through a command you supply that holds your own key, and saves the replies next to the recorded ones. It is never used by the test. Replay the new session with your `run_plan` and the same approvals, and note which model, date and temperature produced it.
