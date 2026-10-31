"""Build the data for capstone 10-01: the Pottlemere quarterly business review.

Pottlemere is a fictional online shop for kitchenware (pans, knives, storage
jars) that sells across India in rupees. The data is synthetic and
deterministic (fixed seed). It is the raw export the analyst receives on
26 October 2026, mess included:

data/orders.csv     one row per LOAD of an order: order_id, customer_id,
                    order_date, status, platform, amount, loaded_at.
data/refunds.csv    one row per load of a refund: refund_id, order_id,
                    refund_date, refund_amount, loaded_at.
data/customers.csv  one row per load of a customer: customer_id, signup_date,
                    acquisition_channel, city.

The mess planted in it:
- Duplicates. Some orders are loaded twice with identical values (a double
  write). Some are loaded again later with a new status: an order first
  loaded as completed is reloaded as cancelled. The latest load wins.
  Refunds and customers also have repeated rows.
- Late rows. Most rows load the day after they happen; a few load 5 to 40
  days late. The Q2 report was run on 3 July 2026 and missed them.
- A definition change halfway. On 1 August 2026 the shop moved to a new
  checkout platform. Rows with platform "legacy" store amount INCLUDING the
  12% tax used in this synthetic data; rows with platform "v2" store it
  EXCLUDING tax. Refund amounts always exclude tax.
- A few orders whose customer_id is missing from customers.csv.

The story in it: paid social was paused for Q3, so fewer new customers
arrive, while returning customers keep buying. Basket size does not change.

    python3 make_data.py                         writes the three CSVs (seed 1001)
    import make_data; make_data.build(seed=7)    returns the rows for another seed
"""
import csv
import datetime
import os
import random

SEED = 1001
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
START = datetime.date(2026, 1, 1)
END = datetime.date(2026, 9, 30)
EXPORT = datetime.date(2026, 10, 26)
PLATFORM_SWITCH = datetime.date(2026, 8, 1)
TAX = 0.12
CITIES = ["Pune", "Mumbai", "Bengaluru", "Delhi", "Hyderabad", "Chennai"]
# mean new customers per day, by acquisition channel and quarter
NEW_PER_DAY = {
    "search": {1: 1.2, 2: 1.25, 3: 1.25},
    "referral": {1: 0.45, 2: 0.5, 3: 0.55},
    "social": {1: 0.8, 2: 1.0, 3: 0.25},
}
REPEAT_PER_DAY = 0.0075
ORDER_FIELDS = ["order_id", "customer_id", "order_date", "status", "platform", "amount", "loaded_at"]
REFUND_FIELDS = ["refund_id", "order_id", "refund_date", "refund_amount", "loaded_at"]
CUSTOMER_FIELDS = ["customer_id", "signup_date", "acquisition_channel", "city"]


def poisson(rng, lam):
    """A Poisson draw by counting uniform products (fine for small lam)."""
    limit, k, p = pow(2.718281828459045, -lam), 0, 1.0
    while True:
        p *= rng.random()
        if p < limit:
            return k
        k += 1


def load_day(rng, day):
    """When a row dated `day` reaches the warehouse: usually the next day, sometimes weeks late."""
    if rng.random() < 0.05:
        return day + datetime.timedelta(days=rng.randint(5, 40))
    return day + datetime.timedelta(days=1)


def build(seed=SEED):
    """Return {"orders": [...], "refunds": [...], "customers": [...]}, each row a dict of text values."""
    rng = random.Random(seed)
    customers, true_orders = [], []
    active = []  # (customer_id, first order date)
    day = START
    while day <= END:
        q = (day.month - 1) // 3 + 1
        todays = []
        for cid, _ in active:
            if rng.random() < REPEAT_PER_DAY:
                todays.append(cid)
        for channel in ("search", "referral", "social"):
            for _ in range(poisson(rng, NEW_PER_DAY[channel][q])):
                cid = "C%05d" % (len(customers) + 1)
                signup = day - datetime.timedelta(days=rng.choice([0, 0, 0, 1, 2, 5]))
                customers.append({"customer_id": cid, "signup_date": signup.isoformat(),
                                  "acquisition_channel": channel, "city": rng.choice(CITIES)})
                active.append((cid, day))
                todays.append(cid)
        for cid in todays:
            net = round(rng.lognormvariate(7.35, 0.55))
            true_orders.append((cid, day, net))
        day += datetime.timedelta(days=1)

    orders, refunds = [], []
    for n, (cid, day, net) in enumerate(true_orders, 1):
        oid = "P%06d" % n
        platform = "v2" if day >= PLATFORM_SWITCH else "legacy"
        amount = "%.2f" % (net * (1 + TAX) if platform == "legacy" else net)
        status = "cancelled" if rng.random() < 0.04 else "completed"
        loaded = load_day(rng, day)
        row = {"order_id": oid, "customer_id": cid, "order_date": day.isoformat(), "status": status,
               "platform": platform, "amount": amount, "loaded_at": loaded.isoformat()}
        loads = [row]
        r = rng.random()
        if r < 0.02:
            loads.append(dict(row))  # double write, same load date
        elif r < 0.05 and status == "completed":
            later = loaded + datetime.timedelta(days=rng.randint(2, 20))
            loads.append(dict(row, status="cancelled", loaded_at=later.isoformat()))
            status = "cancelled"
        elif r < 0.07:
            later = loaded + datetime.timedelta(days=rng.randint(1, 10))
            loads.append(dict(row, loaded_at=later.isoformat()))  # re-export, nothing changed
        orders.extend(x for x in loads if x["loaded_at"] <= EXPORT.isoformat())
        if status == "completed" and rng.random() < 0.07:
            rday = day + datetime.timedelta(days=rng.randint(3, 30))
            share = rng.choice([0.3, 0.5, 1.0, 1.0])
            rrow = {"refund_id": "R%06d" % (len(refunds) + 1), "order_id": oid, "refund_date": rday.isoformat(),
                    "refund_amount": "%.2f" % (net * share), "loaded_at": load_day(rng, rday).isoformat()}
            if rrow["loaded_at"] <= EXPORT.isoformat():
                refunds.append(rrow)
                if rng.random() < 0.05:
                    refunds.append(dict(rrow))

    out_customers = []
    for c in customers:
        if rng.random() < 0.01:
            continue  # lost in the customer sync: orders point at a customer we cannot see
        out_customers.append(c)
        if rng.random() < 0.03:
            out_customers.append(dict(c))
    orders.sort(key=lambda x: (x["loaded_at"], x["order_id"]))
    refunds.sort(key=lambda x: (x["loaded_at"], x["refund_id"]))
    return {"orders": orders, "refunds": refunds, "customers": out_customers}


def write_csv(rows, fields, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_all(data, folder):
    write_csv(data["orders"], ORDER_FIELDS, os.path.join(folder, "orders.csv"))
    write_csv(data["refunds"], REFUND_FIELDS, os.path.join(folder, "refunds.csv"))
    write_csv(data["customers"], CUSTOMER_FIELDS, os.path.join(folder, "customers.csv"))


def main():
    data = build()
    write_all(data, DATA)
    print("wrote", len(data["orders"]), "order rows,", len(data["refunds"]), "refund rows and",
          len(data["customers"]), "customer rows to", DATA)


if __name__ == "__main__":
    main()
