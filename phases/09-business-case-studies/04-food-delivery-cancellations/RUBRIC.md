# Rubric: steps 10 to 12 of the cancellations case

The test checks your numbers (steps 7 to 9). This rubric checks what you do with them. Score each row 0, 1 or 2. A total of 5 or 6 is ready to send to Rohan; 3 or 4 needs one more pass; below 3, start again from your step 9.

| Step | 0 points | 1 point | 2 points |
|---|---|---|---|
| 10. Recommendation is specific | "Investigate the app" or "improve customer experience". No owner, no action, no time | Names the action (roll back 7.4.0) but not where, who or when, or also recommends the fee or a rider programme | One action with an owner and a time: pause the 7.4.0 rollout and roll Nagpur back to 7.3.2 now, hold the release for other cities, and do not launch the cancellation fee |
| 11. Impact is sized with a stated assumption | No number, or a number with no way to check it ("saves lakhs") | A number from the data (about 47 extra cancellations in six weeks) but no money, or money with an unstated order value | Cancellations avoided per week from the data (about 11 at full adoption), turned into money with the assumption written down (for example Rs 300 order value, 20% commission), plus the avoided risk of a four-city rollout |
| 12. Limitations are honest | None, or generic ("data may have errors") | One real limit, such as "we did not see crash logs" | At least two limits specific to this case and what result would change the answer: the data locates the cause but does not prove the mechanism; Nagpur's small before sample; early updaters may differ; what would happen to 7.3.2 users after a rollback if the city were the cause |

## Checks before you send

- Every number in your recommendation appears in your step 9 output or is labelled as an assumption.
- The recommendation says what NOT to do (the fee), because someone in the room is proposing it.
- You used rates per order, not counts or shares of cancellations, in every comparison.

## A two-point answer, in short

"Roll Nagpur back to 7.3.2 today and hold 7.4.0 everywhere else until product finds the bug; no cancellation fee. This avoids about 11 cancelled orders a week in Nagpur (about Rs 660 of commission at an assumed Rs 300 order and 20% commission), and prevents roughly 55 a week if the release had gone to all four cities. Caveat: we located the cause but have not seen the app logs that prove it; if Nagpur cancellations stay high after the rollback, the cause is the city, not the app."
