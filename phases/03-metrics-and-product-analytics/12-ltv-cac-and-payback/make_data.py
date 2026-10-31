"""Build three files for a synthetic subscription workout app. Customers start a
paid plan between January and September 2026; payments are recorded up to and
including October 2026.

customers.csv: customer_id, signup_month, channel
payments.csv:  customer_id, month, amount     (one row per paid month)
spend.csv:     month, channel, spend          (marketing spend, January to September)

The data is synthetic and deterministic (fixed seed). Customers pay every month from
their signup month until they cancel; once they cancel they do not come back. Paid
social brings many customers at a high cost and they cancel fast; referral customers
are cheap (a fixed bonus per referral) and stay longest. "brand" spend (podcast and
outdoor ads) is not tied to any channel's customers.

    python3 make_data.py          writes the three files (seed 71)
    import make_data; make_data.build(seed=3)   returns the rows for another seed
"""
import csv
import os
import random

SEED = 71
HERE = os.path.dirname(os.path.abspath(__file__))
FIELDS = {"customers": ["customer_id", "signup_month", "channel"],
          "payments": ["customer_id", "month", "amount"],
          "spend": ["month", "channel", "spend"]}
SIGNUP_MONTHS = ["2026-%02d" % m for m in range(1, 10)]
AS_OF = "2026-10"
# channel: (new customers per month, monthly cancel probability, spend per new customer)
CHANNELS = {"paid_social": (14, 0.16, 86.0), "search": (10, 0.08, 44.0), "referral": (6, 0.06, 15.0)}
BRAND_SPEND = 600.0
PLANS = ((12.0, 0.7), (20.0, 0.3))


def next_month(month):
    y, m = int(month[:4]), int(month[5:])
    return "%04d-%02d" % (y + (m == 12), m % 12 + 1)


def build(seed=SEED):
    """Return {"customers": [...], "payments": [...], "spend": [...]}, rows of text values."""
    rng = random.Random(seed)
    customers, payments, spend = [], [], []
    cid = 0
    for month in SIGNUP_MONTHS:
        for channel in sorted(CHANNELS):
            per_month, cancel, cost = CHANNELS[channel]
            n = max(1, per_month + rng.randint(-3, 3))
            for _ in range(n):
                cid += 1
                customer = "c%04d" % cid
                customers.append({"customer_id": customer, "signup_month": month, "channel": channel})
                price = PLANS[0][0] if rng.random() < PLANS[0][1] else PLANS[1][0]
                m = month
                while True:
                    payments.append({"customer_id": customer, "month": m, "amount": "%.2f" % price})
                    if m == AS_OF or rng.random() < cancel:
                        break
                    m = next_month(m)
            if channel == "referral":
                amount = cost * n                      # a fixed bonus per referred customer
            else:
                amount = cost * n * rng.uniform(0.85, 1.15)
            spend.append({"month": month, "channel": channel, "spend": "%.2f" % amount})
        spend.append({"month": month, "channel": "brand", "spend": "%.2f" % (BRAND_SPEND * rng.uniform(0.9, 1.1))})
    payments.sort(key=lambda r: (r["month"], r["customer_id"]))
    return {"customers": customers, "payments": payments, "spend": spend}


def write_csv(rows, path, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_all(tables, folder):
    for name in ("customers", "payments", "spend"):
        write_csv(tables[name], os.path.join(folder, name + ".csv"), FIELDS[name])


def main():
    tables = build()
    write_all(tables, os.path.join(HERE, "data"))
    print("wrote", ", ".join("%d %s" % (len(tables[k]), k) for k in ("customers", "payments", "spend")))


if __name__ == "__main__":
    main()
