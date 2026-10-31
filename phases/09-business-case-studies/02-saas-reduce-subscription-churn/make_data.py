"""Build data/customers.csv for the Tallyfern churn case.

Tallyfern is a fictional invoicing and bookkeeping app for small businesses,
sold per seat (one seat per user) on a monthly or an annual plan. One row per
customer who signed up from January 2025 to September 2026. The data is
observed at the end of October 2026. It is synthetic and deterministic
(fixed seed).

Columns: customer_id, signup_month (YYYY-MM), plan (monthly or annual), seats,
mrr (monthly recurring revenue in rupees: 450 a seat on monthly, 375 a seat on
annual), onboarded (yes if the customer connected a bank feed in the first
14 days, else no), churn_month (the month the subscription ended, blank if
still active at the end of October 2026).

The story planted in the data:
- Customers who never onboard churn heavily in their first three months
  (monthly plan) or at their first renewal (annual plan).
- Small accounts (1 or 2 seats) churn more often than teams, every month,
  but they pay little.
- Annual customers can only leave at a renewal (month 12 or 24).

    python3 make_data.py                         writes data/customers.csv (seed 211)
    import make_data; make_data.build(seed=12)   returns the rows for another seed
"""
import csv
import os
import random

SEED = 211
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "customers.csv")
FIELDS = ["customer_id", "signup_month", "plan", "seats", "mrr", "onboarded", "churn_month"]
SIGNUPS = [(2025, m) for m in range(1, 13)] + [(2026, m) for m in range(1, 10)]
END = (2026, 10)
PRICE = {"monthly": 450, "annual": 375}


def month_index(year, month):
    return year * 12 + month - 1


def month_name(index):
    return "%04d-%02d" % (index // 12, index % 12 + 1)


def hazard(plan, small, onboarded, tenure):
    """Chance of leaving in tenure month `tenure` (1 = the first month after signup)."""
    if plan == "annual":
        if tenure % 12 != 0:
            return 0.0
        return 0.10 + (0.12 if small else 0.0) + (0.0 if onboarded else 0.35)
    h = 0.015 + (0.025 if small else 0.0)
    if not onboarded:
        h += 0.14 if tenure <= 3 else 0.01
    return h


def build(seed=SEED):
    """Return {"customers": [row, ...]}, each row a dict of text values as written to the CSV."""
    rng = random.Random(seed)
    rows = []
    n = 0
    end = month_index(*END)
    for year, month in SIGNUPS:
        start = month_index(year, month)
        for _ in range(int(round(rng.gauss(78, 6)))):
            n += 1
            plan = "annual" if rng.random() < 0.30 else "monthly"
            small = rng.random() < 0.55
            seats = rng.randint(1, 2) if small else min(25, 3 + int(rng.expovariate(1 / 5.0)))
            onboarded = rng.random() < 0.65
            churn = ""
            for tenure in range(1, end - start + 1):
                if rng.random() < hazard(plan, small, onboarded, tenure):
                    churn = month_name(start + tenure)
                    break
            rows.append({
                "customer_id": "C%05d" % n,
                "signup_month": month_name(start),
                "plan": plan,
                "seats": str(seats),
                "mrr": str(seats * PRICE[plan]),
                "onboarded": "yes" if onboarded else "no",
                "churn_month": churn,
            })
    return {"customers": rows}


def write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    rows = build()["customers"]
    write_csv(rows, OUT)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
