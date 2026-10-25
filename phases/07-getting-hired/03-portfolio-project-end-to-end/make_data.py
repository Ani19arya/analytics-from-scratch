"""Build data/subscriptions.csv for a fictional meal kit subscription, Pantrybox.

Columns: customer_id, signup_date, start_type (trial or paid), plan (monthly or annual),
         cancel_date (blank while still subscribed).
Data is as of 2026-10-01. Customers signed up between 2026-01-01 and 2026-08-31,
so the newest ones have not had 90 days to churn yet.
The data is synthetic and deterministic (fixed seed).
Run from the lesson folder: python3 make_data.py
"""
import csv
import datetime
import os
import random

random.seed(3030)

HERE = os.path.dirname(os.path.abspath(__file__))
AS_OF = datetime.date(2026, 10, 1)
START = datetime.date(2026, 1, 1)
DAYS = (datetime.date(2026, 8, 31) - START).days + 1
# chance of cancelling within 90 days, by start type and plan
CHURN_90 = {("trial", "monthly"): 0.34, ("trial", "annual"): 0.12,
            ("paid", "monthly"): 0.24, ("paid", "annual"): 0.08}


def main():
    rows = []
    for cid in range(1, 1401):
        signup = START + datetime.timedelta(days=random.randrange(DAYS))
        start_type = "trial" if random.random() < 0.55 else "paid"
        plan = "annual" if random.random() < 0.2 else "monthly"
        cancel = None
        if random.random() < CHURN_90[(start_type, plan)]:
            cancel = signup + datetime.timedelta(days=random.randint(3, 90))
        elif random.random() < 0.15:
            cancel = signup + datetime.timedelta(days=random.randint(91, 260))
        if cancel is not None and cancel > AS_OF:
            cancel = None
        rows.append([cid, signup.isoformat(), start_type, plan, cancel.isoformat() if cancel else ""])
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(os.path.join(HERE, "data", "subscriptions.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["customer_id", "signup_date", "start_type", "plan", "cancel_date"])
        w.writerows(rows)
    print("wrote %d customers" % len(rows))


if __name__ == "__main__":
    main()
