"""Build the synthetic tables for lesson 05: Tiffinbell customers and orders around
October 2026.

data/customers.csv: customer_id, email, is_test (1 for staff test accounts),
                    deleted_at (UTC time the customer deleted their account, blank if not)
data/orders.csv:    order_id, customer_id, created_at (UTC, like 2026-10-01T18:45:00Z),
                    status (delivered or cancelled), amount (rupees),
                    refunded_amount (rupees, blank when there was no refund)

A few customers asked for their data to be erased: their customers row is gone,
but their orders keep the customer_id. Some orders are free meals (amount 0).
Orders run from 28 September to 2 November 2026 (UTC), so both month edges are in
the data, and seven customers order only once, just after midnight India time on
1 October or 1 November. The data is synthetic; no row is a real person.

Run: python3 make_data.py          (writes both CSVs for the default seed)
Use: build(seed) returns {"customers": rows, "orders": rows} without writing anything.
"""
import csv
import datetime
import os
import random

DEFAULT_SEED = 3055
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIELDS = {"customers": ["customer_id", "email", "is_test", "deleted_at"],
          "orders": ["order_id", "customer_id", "created_at", "status", "amount", "refunded_amount"]}
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
FIRST_DAY = datetime.date(2026, 9, 28)
DAYS = 36                      # 28 Sep to 2 Nov
REGULAR, TESTERS, ERASED = 240, 5, 4
# Customers whose only order is a late night order just after midnight India time on
# 1 October (still 30 September in UTC) or on 1 November (still 31 October in UTC).
EDGE_DAYS = [datetime.date(2026, 10, 1)] * 4 + [datetime.date(2026, 11, 1)] * 3
STAMP = "%Y-%m-%dT%H:%M:%SZ"


def to_utc_text(local):
    return local.astimezone(datetime.timezone.utc).strftime(STAMP)


def order_time(rng, day):
    """A local (India) time on `day`: lunch, dinner, or a late night order just after midnight."""
    slot = rng.random()
    if slot < 0.35:
        minutes = rng.randint(12 * 60, 14 * 60 + 59)
    elif slot < 0.85:
        minutes = rng.randint(19 * 60, 23 * 60 + 59)
    else:
        day = day + datetime.timedelta(days=1)
        minutes = rng.randint(0, 59)
    return datetime.datetime(day.year, day.month, day.day, minutes // 60, minutes % 60, rng.randint(0, 59), tzinfo=IST)


def build(seed=DEFAULT_SEED):
    """Return {"customers": rows, "orders": rows}. The same seed always gives the same rows."""
    rng = random.Random(seed)
    customers, orders = [], []
    total = REGULAR + TESTERS + ERASED
    for cid in range(1, total + 1):
        is_test = REGULAR < cid <= REGULAR + TESTERS
        erased = cid > REGULAR + TESTERS
        deleted_at = ""
        if not is_test and not erased and rng.random() < 0.05:
            deleted = datetime.datetime(2026, 10, rng.randint(5, 30), rng.randint(0, 23), rng.randint(0, 59),
                                        tzinfo=datetime.timezone.utc)
            deleted_at = deleted.strftime(STAMP)
        if not erased:
            email = ("qa%d@tiffinbell.test" % cid) if is_test else ("customer%d@example.com" % cid)
            customers.append({"customer_id": cid, "email": email, "is_test": 1 if is_test else 0,
                              "deleted_at": deleted_at})
        rate = 0.6 if is_test else rng.choice([0.0, 0.01, 0.02, 0.04, 0.08, 0.15])
        if erased:
            rate = 0.08
        for offset in range(DAYS):
            if rng.random() >= rate:
                continue
            local = order_time(rng, FIRST_DAY + datetime.timedelta(days=offset))
            status = "cancelled" if rng.random() < 0.12 else "delivered"
            amount = 0 if rng.random() < 0.03 else rng.randint(12, 90) * 10
            refunded = ""
            if status == "delivered" and amount > 0:
                r = rng.random()
                if r < 0.06:
                    refunded = amount
                elif r < 0.10:
                    refunded = rng.randint(1, amount // 20) * 10
            orders.append({"customer_id": cid, "created_at": to_utc_text(local), "status": status,
                           "amount": amount, "refunded_amount": refunded})
    for cid, day in enumerate(EDGE_DAYS, total + 1):
        customers.append({"customer_id": cid, "email": "customer%d@example.com" % cid, "is_test": 0,
                          "deleted_at": ""})
        local = datetime.datetime(day.year, day.month, day.day, 0, rng.randint(0, 59), rng.randint(0, 59),
                                  tzinfo=IST)
        orders.append({"customer_id": cid, "created_at": to_utc_text(local), "status": "delivered",
                       "amount": rng.randint(12, 90) * 10, "refunded_amount": ""})
    orders.sort(key=lambda o: (o["created_at"], o["customer_id"]))
    for oid, order in enumerate(orders, 1):
        order["order_id"] = oid
    return {"customers": customers, "orders": orders}


def write_csv(path, fieldnames, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def write_all(folder, tables):
    for name, rows in tables.items():
        write_csv(os.path.join(folder, name + ".csv"), FIELDS[name], rows)


def main():
    tables = build()
    write_all(DATA, tables)
    for name, rows in tables.items():
        print("wrote", len(rows), "rows to", os.path.join(DATA, name + ".csv"))


if __name__ == "__main__":
    main()
