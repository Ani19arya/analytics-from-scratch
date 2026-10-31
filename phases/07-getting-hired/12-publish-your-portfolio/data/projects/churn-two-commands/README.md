# Do trial customers churn more?

## Question

Do customers who start on a free trial cancel within 90 days more often than customers who pay from day one?

## Method

I counted churned customers by start type and compared the two rates. The comparison is observational: customers chose how to start.

## Answer

Within 90 days, 20.7% of trial starters (6 of 29) churned, against 28.6% of paid starters (8 of 28).

## Data

`data/customers.csv`, one row per customer. Synthetic data made for this course. Licence: MIT, the same as the code.

## How to run

```
pip install -r requirements.txt
python3 analysis.py
```
