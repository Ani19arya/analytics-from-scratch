"""Build data/subscriptions.csv for a fictional meal kit subscription, Pantrybox.

Columns: customer_id, signup_date, start_type (trial or paid), plan (monthly or annual),
         cancel_date (blank while still subscribed).

How the data is made:
- A trial starter gets 14 free days (signup day plus 13). The first charge is on day 14.
  Some cancel during the trial and never pay. The rest become paying customers on day 14.
- A paid starter pays from the signup day.
- A paying customer may then cancel within 90 days of their first paid day, at a rate
  that depends on start type and plan, or later, or not at all.
Data is as of 2026-10-01. Customers signed up between 2026-01-01 and 2026-08-31,
so the newest ones have not had 90 paid days yet.
The data is synthetic and deterministic (fixed seed).
Run from the lesson folder: python3 make_data.py
In code: build(seed) returns the rows without writing files.
"""
import csv
import datetime
import os
import random

SEED = 3030
HERE = os.path.dirname(os.path.abspath(__file__))
AS_OF = datetime.date(2026, 10, 1)
START = datetime.date(2026, 1, 1)
DAYS = (datetime.date(2026, 8, 31) - START).days + 1
TRIAL_DAYS = 14
# chance a trial starter cancels during the free trial, by plan
TRIAL_DROP = {"monthly": 0.30, "annual": 0.18}
# chance a paying customer cancels within 90 days of the first paid day
PAID_CHURN_90 = {("trial", "monthly"): 0.29, ("trial", "annual"): 0.10,
                 ("paid", "monthly"): 0.24, ("paid", "annual"): 0.08}
HEADER = ["customer_id", "signup_date", "start_type", "plan", "cancel_date"]


def build(seed=SEED):
    """List of rows [customer_id, signup_date, start_type, plan, cancel_date or '']."""
    rng = random.Random(seed)
    rows = []
    for cid in range(1, 1401):
        signup = START + datetime.timedelta(days=rng.randrange(DAYS))
        start_type = "trial" if rng.random() < 0.55 else "paid"
        plan = "annual" if rng.random() < 0.2 else "monthly"
        cancel = None
        first_paid = signup
        if start_type == "trial":
            first_paid = signup + datetime.timedelta(days=TRIAL_DAYS)
            if rng.random() < TRIAL_DROP[plan]:
                cancel = signup + datetime.timedelta(days=rng.randint(1, TRIAL_DAYS - 1))
        if cancel is None:
            if rng.random() < PAID_CHURN_90[(start_type, plan)]:
                cancel = first_paid + datetime.timedelta(days=rng.randint(1, 90))
            elif rng.random() < 0.15:
                cancel = first_paid + datetime.timedelta(days=rng.randint(91, 260))
        if cancel is not None and cancel > AS_OF:
            cancel = None
        rows.append([cid, signup.isoformat(), start_type, plan, cancel.isoformat() if cancel else ""])
    return rows


def main():
    rows = build()
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(os.path.join(HERE, "data", "subscriptions.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)
    print("wrote %d customers" % len(rows))


if __name__ == "__main__":
    main()
