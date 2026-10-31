"""Build data/payments.csv: a synthetic Q3 2026 payments export for Lanternway Courses.

Run from the lesson folder: python3 make_data.py
One row per payment, July to September 2026. The data is synthetic and deterministic.

The problems are added on purpose, the way a reloaded warehouse table gets them:
- three days of payments loaded twice (a re-run load: exact copies), and one payment id
  used by two different payments;
- missing amounts written three ways: an empty cell, "NULL" and "N/A";
- a blank plan, and plan names in mixed case;
- a payment of 4,900.00 (49.00 typed with two extra zeros), refunds written as negative
  amounts on "paid" rows;
- a few payments dated outside Q3;
- one amount written with a decimal comma ("149,00"), which is text, not a number.
Country "NA" is Namibia, a real value, not a missing one.

    build(seed)     -> {"payments": rows}  (every cell is text, as csv.DictReader gives it)
    expected(seed)  -> the generator's own record of what it broke, for the test
"""
import csv
import os
import random
from datetime import date, timedelta

DEFAULT_SEED = 505
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIELDS = ["payment_id", "customer_id", "paid_at", "plan", "amount", "country", "status"]
PLANS = {"Basic": "19.00", "Pro": "49.00", "Team": "149.00"}
COUNTRIES = ["US", "US", "US", "IN", "IN", "GB", "CA", "DE"]


def _generate(seed):
    rng = random.Random(seed)
    n = rng.randint(560, 640)
    rows = []
    for i in range(n):
        plan = rng.choice(["Basic", "Basic", "Pro", "Pro", "Pro", "Team"])
        d = date(2026, 7, 1) + timedelta(days=rng.randint(0, 91))
        rows.append({"payment_id": "PAY-%05d" % (10001 + i), "customer_id": "C%04d" % rng.randint(1, 450),
                     "paid_at": d.isoformat(), "plan": plan, "amount": PLANS[plan],
                     "country": "NA" if rng.random() < 0.015 else rng.choice(COUNTRIES), "status": "paid" if rng.random() < 0.95 else "refunded"})
    # Every kind of problem, on distinct rows chosen at random. How many of each varies by seed.
    names = ["empty_amount", "null_text_amount", "na_text_amount", "blank_plan", "case_plan", "huge_amount",
             "negative_amount", "outside_q3", "comma_amount", "conflict"]
    sizes = [rng.randint(2, 4), rng.randint(1, 3), 1, rng.randint(1, 2), rng.randint(3, 5), 1,
             rng.randint(1, 3), rng.randint(1, 3), 1, 1]
    picks = rng.sample(range(n), sum(sizes))
    log, at = {}, 0
    for name, size in zip(names, sizes):
        log[name], at = picks[at:at + size], at + size
    first_day = date(2026, 8, 1) + timedelta(days=rng.randint(0, 25))
    rerun = {(first_day + timedelta(days=k)).isoformat() for k in range(3)}
    log["exact_dupes"] = [i for i in range(n) if rows[i]["paid_at"] in rerun and i not in picks]
    for i in log["empty_amount"]:
        rows[i]["amount"] = ""
    for i in log["null_text_amount"]:
        rows[i]["amount"] = "NULL"
    for i in log["na_text_amount"]:
        rows[i]["amount"] = "N/A"
    for i in log["blank_plan"]:
        rows[i]["plan"] = "  "
    for i in log["case_plan"]:
        rows[i]["plan"] = rows[i]["plan"].lower() if rng.random() < 0.5 else rows[i]["plan"].upper()
    for i in log["huge_amount"]:
        rows[i]["amount"], rows[i]["plan"] = "4900.00", "Pro"
    for i in log["negative_amount"]:
        rows[i]["amount"] = "-" + PLANS["Pro"]
        rows[i]["plan"] = "Pro"
    for i in log["outside_q3"]:
        rows[i]["paid_at"] = rng.choice(["2026-10-01", "2026-10-02", "2025-07-14"])
    for i in log["comma_amount"]:
        rows[i]["amount"] = PLANS[rows[i]["plan"].strip().title() or "Pro"].replace(".", ",")
    # One payment id reused by a different payment, and four payments loaded twice.
    conflict_src = log["conflict"][0]
    other = dict(rows[(conflict_src + 1) % n])
    other["payment_id"] = rows[conflict_src]["payment_id"]
    out = list(rows)
    out.insert(conflict_src + 1, other)
    for i in sorted(log["exact_dupes"], reverse=True):
        target = out.index(rows[i])
        out.insert(target + 1, dict(rows[i]))
    return out, rows, log


def build(seed=DEFAULT_SEED):
    return {"payments": _generate(seed)[0]}


def expected(seed=DEFAULT_SEED):
    """What the generator did, counted from its own log."""
    out, rows, log = _generate(seed)
    return {"rows": len(out), "duplicate_key_rows": 1 + len(log["exact_dupes"]),
            "exact_duplicate_rows": len(log["exact_dupes"])}


def main():
    os.makedirs(DATA, exist_ok=True)
    rows = build()["payments"]
    with open(os.path.join(DATA, "payments.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/payments.csv" % len(rows))


if __name__ == "__main__":
    main()
