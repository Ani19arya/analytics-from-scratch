# Rubric: capstone 10-06, the Parcelwick weekly pipeline

The test checks the numbers and the pipeline's behaviour. This rubric scores everything else in [DELIVERABLES.md](DELIVERABLES.md). Score each row 0, 1 or 2. Out of 14: 12 or more is ready to hand over; 8 to 11 needs one more pass; below 8, go back to the checks and the runbook.

| Area | 0 points | 1 point | 2 points |
|---|---|---|---|
| 1. Framing | A script that prints numbers, with no link to Owen's three rules | Two of the three rules met and shown (never wrong quietly, never twice, say when numbers change) | All three met and shown with evidence from your outbox: an alert instead of a report, a skipped re-run, a restated note |
| 2. Data handling | Counts rows, or filters on one outcome spelling | Latest outcome per parcel, but the code change or the re-sent file is handled by luck rather than by a rule | Every mess in the notes has a named rule and a check: latest outcome wins, both code sets mapped and unknowns blocked, the copy file harmless by design, late rows restated |
| 3. Checks | No checks, or every check blocks | Checks exist but the error and warning line is arbitrary, or a warning never reaches the reader | Errors are the problems that make every number wrong (schema, unknown codes, empty or collapsed volume); warnings are problems a reader can work around (a silent site); each is a sentence a non-analyst understands |
| 4. Report design | A dump of numbers with no comparison | Comparisons, but percent change on rates or on tiny counts, or the silent site hidden in the totals | Summary block first, change in points for rates, a by-site table with a short trend that makes Bedminster visible, the restated note, and the silent site named next to the totals it lowers |
| 5. Reliability | Re-running sends again, or output differs run to run | Idempotent, but a blocked week is recorded as sent, or state lives somewhere that is easy to lose | Idempotent, deterministic, a blocked week retried next run, state small and human-readable, and a documented way to re-send on purpose |
| 6. Runbook | None | Steps to run it, but not what to do when it is blocked | Schedule, each check and its fix, how to re-send and re-run, what to back up, written so Femi's replacement needs nobody |
| 7. Honesty about limits | Claims the newest week is final | Mentions late rows but not their size or direction | Sizes the restatement (for example, 179 parcels sent, 186 now for the week of 12 October), names the silent site's effect on the totals, and says which numbers are still moving |

## Checks before you hand over

- Run the same week twice: one email.
- Break a copy of the data: an alert, no report, and the next run tries again.
- Read your email as Owen: can he see Bedminster without asking?
- Nothing in the pipeline opens a network connection.
