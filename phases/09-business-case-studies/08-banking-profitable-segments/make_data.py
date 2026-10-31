"""Build data/customers.csv and data/rates.csv for the Corriebrook Bank
segment profitability case.

The data is synthetic and deterministic (fixed seed). Corriebrook Bank is a
fictional retail bank. One row per customer for the 12 months from October
2025 to September 2026. Money is in GBP.

customers.csv: customer_id, segment, deposit_balance (average over the year),
loan_balance (average over the year), fee_income (fees paid in the year),
branch_visits, calls (to the contact centre), digital_sessions (app and web
logins), charge_off (loan amount written off in the year, 0 for most).

rates.csv: item, value. An example rate card, fictional, not any real bank's:
the margin the bank earns per GBP of average deposit and loan balance a year,
the cost of one branch visit, one call and one digital session, and a fixed
yearly cost per customer (statements, systems, compliance).

The story planted in the data:
- Retirees keep good balances but use the branch heavily. With costs split
  evenly per customer they look profitable; costed by what they actually
  use, they lose money.
- Students use the app all the time and the branch almost never, so they
  are cheap to serve, though their small balances still do not cover it.
- Profit is concentrated: a minority of customers earns more than the total.

    python3 make_data.py                        writes data/*.csv (seed 808)
    import make_data; make_data.build(seed=5)   returns the rows for another seed
"""
import csv
import math
import os
import random

SEED = 808
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CUSTOMER_FIELDS = ["customer_id", "segment", "deposit_balance", "loan_balance", "fee_income",
                   "branch_visits", "calls", "digital_sessions", "charge_off"]
RATE_FIELDS = ["item", "value"]
RATES = [("deposit_margin", "0.025"), ("loan_margin", "0.035"), ("branch_visit", "14.00"),
         ("call", "5.50"), ("digital_session", "0.08"), ("account_fixed", "36.00")]

# segment: (customers, median deposit, share with a loan, median loan, median fees,
#           branch visits, calls, digital sessions, chance a loan is charged off)
SEGMENTS = [
    ("Students", 260, 700, 0.20, 1500, 12, 0.6, 1.5, 320, 0.06),
    ("Young professionals", 330, 4200, 0.55, 7000, 45, 1.2, 2.5, 260, 0.03),
    ("Families", 300, 5500, 0.70, 9000, 70, 4.0, 5.0, 190, 0.025),
    ("Retirees", 260, 8000, 0.10, 3000, 25, 19.0, 6.0, 15, 0.01),
    ("Small business", 120, 22000, 0.65, 25000, 260, 11.0, 18.0, 380, 0.05),
    ("Premier", 80, 55000, 0.45, 18000, 180, 2.0, 9.0, 300, 0.005),
]


def poisson(rng, lam):
    if lam > 30:
        return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))
    limit = math.exp(-lam)
    k, p = 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def build(seed=SEED):
    """Return {"customers": [...], "rates": [...]}, rows as dicts of text values."""
    rng = random.Random(seed)
    customers = []
    n = 0
    for seg, count, dep, loan_share, loan, fees, branch, calls, digital, co in SEGMENTS:
        for _ in range(count):
            n += 1
            deposit = dep * math.exp(rng.gauss(0, 0.6))
            has_loan = rng.random() < loan_share
            loan_bal = loan * math.exp(rng.gauss(0, 0.5)) if has_loan else 0.0
            charge = loan_bal * rng.uniform(0.3, 1.0) if has_loan and rng.random() < co else 0.0
            customers.append({
                "customer_id": "C%04d" % n,
                "segment": seg,
                "deposit_balance": "%.2f" % deposit,
                "loan_balance": "%.2f" % loan_bal,
                "fee_income": "%.2f" % (fees * math.exp(rng.gauss(0, 0.5))),
                "branch_visits": str(poisson(rng, branch * math.exp(rng.gauss(0, 0.4)))),
                "calls": str(poisson(rng, calls)),
                "digital_sessions": str(poisson(rng, digital * math.exp(rng.gauss(0, 0.4)))),
                "charge_off": "%.2f" % charge,
            })
    order = list(range(len(customers)))
    rng.shuffle(order)
    shuffled = [customers[i] for i in order]
    for i, c in enumerate(shuffled, 1):
        c["customer_id"] = "C%04d" % i
    return {"customers": shuffled, "rates": [{"item": k, "value": v} for k, v in RATES]}


def write_csv(rows, fields, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    data = build()
    write_csv(data["customers"], CUSTOMER_FIELDS, os.path.join(DATA, "customers.csv"))
    write_csv(data["rates"], RATE_FIELDS, os.path.join(DATA, "rates.csv"))
    print("wrote", len(data["customers"]), "customers and", len(data["rates"]), "rates to", DATA)


if __name__ == "__main__":
    main()
