# Do trial customers churn more?

## Question

Do customers who start on a free trial cancel within 90 days more often than customers who pay from day one?

## Method

I counted churned customers by start type and compared the two rates. The comparison is observational: customers chose how to start.

## Answer

Within 90 days, 53.3% of trial starters (16 of 30) churned, against 27.3% of paid starters (9 of 33).

## Data

`data/customers.csv`, one row per customer. Synthetic data made for this course. Licence: MIT, the same as the code.

## How to run

```
python3 analysis.py
```

Python 3.9 or later. It prints the two churn rates.
