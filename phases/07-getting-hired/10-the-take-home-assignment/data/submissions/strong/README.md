# Where to put next quarter's marketing budget

North grew the most from September to October: revenue up $3,353.18. October net revenue was $64,581.98, and 30.2% of October customers ordered two or more times.

Recommendation: start the budget conversation with North, and confirm with November before moving money, because one month of growth can be noise.

Synthetic data from a course exercise. Kestrel Home is a fictional company.

## Answers

| Question | Answer |
|---|---|
| October net revenue | $64,581.98 |
| Region that grew the most | North |
| Its growth, September to October | $3,353.18 |
| October customers with 2+ orders | 30.2% |

## Data checks

- 24 rows were duplicates: exact repeats of an earlier order_id (exported twice). Kept one of each.
- 15 orders came from internal test accounts (email ending in @kestrelhome.test), all in October. Removed.
- 32 real orders were refunded. Left out of revenue and of the order counts.

Without these checks October revenue and the top region both come out different.

## Assumptions

- Net revenue means paid orders only, without tax or shipping (the file has one amount per order).
- A month is the calendar month of order_date.
- A customer is a customer_id.

## Limits and next steps

- Two months is one change, not a trend. Check November before moving budget.
- Growth is in dollars, so a large region can lead on a small percentage change. A percentage view is a quick follow-up if Hana prefers it.
- Next: split the growth into more customers versus bigger orders.

Code: `analysis.py` reproduces every number above from orders.csv in one command.
