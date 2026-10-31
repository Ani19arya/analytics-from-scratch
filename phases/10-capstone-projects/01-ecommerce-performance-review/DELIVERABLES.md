# Deliverables: what to hand in

Part of capstone [10-01](README.md). Read [BRIEF.md](BRIEF.md) first.

## 1. The numbers with one right answer (checked by the test)

Fill in every function in `exercise.py`, then run `python3 test_lesson.py` from this folder. The test checks your functions on the committed data, on a second dataset built from another seed, and on small hand-made tables. Use these definitions; they are finance's, and the test uses them too.

| Term | Definition |
|---|---|
| Clean order | One row per `order_id`: the load with the latest `loaded_at`. Only loads on or before the as-of date count when an as-of date is given |
| Sale | A clean order whose latest status is `completed` |
| Net amount | `amount` excluding tax: legacy amounts divided by 1.12, v2 amounts as stored. No rounding per row |
| Net sales of a quarter | Sum of net amounts of sales with `order_date` in the quarter |
| Refunds of a quarter | Sum of `refund_amount` of clean refunds (one per `refund_id`) with `refund_date` in the quarter |
| Net revenue | Net sales minus refunds |
| Orders, customers | Sales in the quarter; distinct `customer_id` among them |
| New customer | A customer whose first sale ever is in the quarter. Returning = customers minus new |
| AOV (average order value) | Net sales / orders |
| Q2 as reported | Computed from the rows loaded on or before 3 July 2026 |
| Q2 restated | Computed from every row in the export |

## 2. The QBR table

One table with three columns: Q2 as reported, Q2 restated, Q3. Rows: orders, customers, new customers, returning customers, net sales, refunds, net revenue, AOV. Add the change from Q2 restated to Q3, in % and in rupees or counts. Compare Q3 with Q2 restated, and say so under the table.

## 3. A reconciliation

A short table that walks Q3 net sales from the raw sum of `amount` to your clean number, one fix per row (duplicates, cancellations, tax), with the amount each fix moved. A reviewer should be able to rebuild your number from it.

## 4. One chart

Monthly net sales excluding tax, January to September 2026, with the y axis starting at zero, a title that says the unit, and a note that the data is synthetic. Any tool. If you want to stay in the standard library, `solution/solution.py` shows a 40-line SVG bar chart to read after you try your own.

## 5. A one-page write-up for Anjali

At most one page, in this order:

1. The headline in two sentences: how Q3 went and the main driver, with numbers.
2. The answer to the August question, with the evidence and how sure you are (include the AOV interval).
3. What changed in Q2 since it was reported, and why.
4. One or two Q4 recommendations, each with an owner, a date and the expected impact. State every assumption behind an impact number.
5. Limits: what the data cannot tell you and what would change your answer.

Score it with [RUBRIC.md](RUBRIC.md). Then read [solution/WRITEUP.md](solution/WRITEUP.md) and compare.
