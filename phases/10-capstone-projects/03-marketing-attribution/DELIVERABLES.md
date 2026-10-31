# Deliverables: what to hand in

Part of capstone [10-03](README.md). Read [BRIEF.md](BRIEF.md) first.

## 1. The numbers with one right answer (checked by the test)

Fill in every function in `exercise.py`, then run `python3 test_lesson.py` from this folder. The test checks your functions on the committed data, on a second dataset built from another seed, and on small hand-made tables. Use these definitions and steps; the test uses them too.

| Term | Definition |
|---|---|
| Spend | One value per week and channel, including the agency fee: display rows before the week of 17 August 2026 are multiplied by 1.15 |
| Order | One per `order_id`, with the order date (from `order_time`) from 29 June to 27 September 2026 |
| Path of an order | The user's touches from 30 days before the order time up to and including the order time, oldest first; equal times are ordered by channel name |
| Attribution models | first: 100% to the first touch. last: 100% to the last. linear: equal shares. position: one touch 100%, two touches 50% each, three or more 40% first, 40% last, 20% split equally over the middle. No touch in the window: 100% to "(none)" |
| Test conversion | Share of a group's users with at least one order dated 3 to 30 August 2026 |
| Lift | Conversion exposed - conversion holdout, with a Wald interval: SE = sqrt(pe (1 - pe) / ne + ph (1 - ph) / nh), 95% = lift +/- 1.96 SE |
| Incremental display orders | Lift x exposed users |
| Calibration factor | Incremental display orders / the linear credit display gets on the exposed users' orders dated 3 to 30 August |

The planning steps, in `plan()`:

1. Weekly linear credit per paid channel (keys: the Monday of the order's week). Multiply display's weekly credit by the calibration factor; leave search and social as they are.
2. For each paid channel, fit conversions = a x sqrt(spend) on its 13 weekly points (spend, calibrated credit) by least squares through the origin: a = sum(y sqrt(x)) / sum(x).
3. Budget = Q3 spend of paid search + paid social + display. Each channel between 50% and 150% of its Q3 spend.
4. Choose the split that maximises predicted conversions: per quarter, sum over channels of a x sqrt(spend / 13) x 13.
5. Report predicted conversions for the Q3 split and for yours.

## 2. The attribution table

For each channel: Q3 spend, credit under each of the four models, cost per order under each, and for display the calibrated credit and cost per order. One sentence under the table saying what the spread between models tells you.

## 3. The test readout

Group sizes, conversion per group, the lift with its 95% interval, incremental orders, and the calibration factor. Say plainly whether the test is precise enough to act on.

## 4. The budget proposal

Q3 spend and proposed Q4 spend per channel, the change in rupees and %, predicted conversions for both, and the marginal cost of one more order in each channel at each split (from the fitted curve: 2 x sqrt(weekly spend) / a).

## 5. One chart

Whatever best defends the split: for example Q3 against proposed spend per channel, or credited against incremental orders for display. Zero baseline, units, "synthetic data".

## 6. A one-page write-up for Sana

At most one page:

1. The proposal in two sentences, with numbers.
2. Why not the agency's split: what last-click attribution measures and what the test shows.
3. How sure you are: the test interval, and what the response curves assume.
4. What to measure in Q4, with an owner and a date.
5. Limits and what would change your answer.

Score it with [RUBRIC.md](RUBRIC.md). Then read [solution/WRITEUP.md](solution/WRITEUP.md) and compare.
