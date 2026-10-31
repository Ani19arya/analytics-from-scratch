"""Build data/applications.csv for the Ledgerlark loan approvals case.

One row per loan application from May 2025 to October 2026 (18 months). The
data is synthetic and deterministic (fixed seed).

Columns: app_id, applied_month (YYYY-MM), score (a credit score, 450 to 799),
loan_amount (requested, in rupees), decision (approved or rejected),
approval_route (policy, test, or blank when rejected), outcome (repaid,
defaulted, open, or blank when rejected).

How the data is made:
- The policy approves every score of 650 or more.
- A random 20% of applicants scoring 550 to 649 are approved as a "test cell",
  so the lender can learn how those applicants behave. Below 550 nobody is
  approved, so no outcome is ever seen there.
- Loans run 6 months. Loans applied for from May 2026 have not finished: their
  outcome is "open".
- The chance of default falls smoothly as the score rises (a logistic curve).

    python3 make_data.py                        writes data/applications.csv (seed 505)
    import make_data; make_data.build(seed=8)   returns the rows for another seed
"""
import csv
import math
import os
import random

SEED = 505
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "applications.csv")
FIELDS = ["app_id", "applied_month", "score", "loan_amount", "decision", "approval_route", "outcome"]
MONTHS = ["2025-%02d" % m for m in range(5, 13)] + ["2026-%02d" % m for m in range(1, 11)]
CUTOFF = 650
TEST_FLOOR = 550
TEST_SHARE = 0.20
OPEN_FROM = "2026-05"


def default_probability(score):
    return 1.0 / (1.0 + math.exp((score - 560) / 38.0))


def build(seed=SEED):
    """Return {"applications": [row, ...]}, each row a dict of text values as written to the CSV."""
    rng = random.Random(seed)
    rows = []
    n = 0
    for month in MONTHS:
        for _ in range(100):
            n += 1
            score = int(round(min(799, max(450, rng.gauss(655, 60)))))
            amount = 1000 * rng.randint(10, 60)
            if score >= CUTOFF:
                route = "policy"
            elif score >= TEST_FLOOR and rng.random() < TEST_SHARE:
                route = "test"
            else:
                route = ""
            bad = rng.random() < default_probability(score)
            if not route:
                outcome = ""
            elif month >= OPEN_FROM:
                outcome = "open"
            else:
                outcome = "defaulted" if bad else "repaid"
            rows.append({
                "app_id": "L%05d" % n,
                "applied_month": month,
                "score": str(score),
                "loan_amount": str(amount),
                "decision": "approved" if route else "rejected",
                "approval_route": route,
                "outcome": outcome,
            })
    return {"applications": rows}


def write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    rows = build()["applications"]
    write_csv(rows, OUT)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
