"""Build the data for the Brackenbee campaign case.

Brackenbee is a fictional online shop for tea, honey and pantry goods. In
September 2026 it ran the "Harvest" campaign: emails and SMS with a 15%
discount code, sent to its customers for four weeks (1 to 28 September). A
random 10% of customers in each segment were held out: they got nothing.
The data is synthetic and deterministic (fixed seed).

data/audience.csv  segment, grp (campaign or holdout), customers.
data/daily.csv     one row per day, segment and grp from 4 August to
                   28 September 2026 (four weeks before the campaign and the
                   four campaign weeks): date, segment, grp, orders,
                   code_orders (orders that used the campaign code),
                   revenue (rupees, after any discount), code_revenue (the
                   part of revenue from code orders, after the discount).

Segments: loyal (three or more orders in the last year), recent (one or two
orders in the last six months), lapsed (no order for six months or more).

The story planted in the data: most code orders come from customers who
would have ordered anyway, above all loyal ones; the campaign adds real
orders mainly among lapsed customers. September is busier than August for
everyone (a seasonal lift), so a before-and-after comparison overstates the
campaign. A few holdout customers find the code on coupon sites.

    python3 make_data.py                        writes both CSVs (seed 315)
    import make_data; make_data.build(seed=4)   returns the rows for another seed
"""
import csv
import datetime
import math
import os
import random

SEED = 315
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
PRE_START = datetime.date(2026, 8, 4)
CAMPAIGN_START = datetime.date(2026, 9, 1)
DAYS = 56
AUDIENCE_FIELDS = ["segment", "grp", "customers"]
DAILY_FIELDS = ["date", "segment", "grp", "orders", "code_orders", "revenue", "code_revenue"]
# customers, campaign-month baseline orders per customer (4 weeks), lift from the
# campaign, share of campaign-group orders that use the code
SEGMENTS = {
    "loyal": {"customers": 12000, "base": 0.20, "lift": 0.02, "code": 0.60},
    "recent": {"customers": 18000, "base": 0.06, "lift": 0.015, "code": 0.60},
    "lapsed": {"customers": 30000, "base": 0.02, "lift": 0.025, "code": 0.75},
}
HOLDOUT_SHARE = 0.10
AUGUST_FACTOR = 0.85   # August is quieter than September
LEAK = 0.05            # share of holdout orders in September that find the code online
DISCOUNT = 0.15


def poisson(rng, lam):
    """Knuth's method: fine for the small daily means used here."""
    limit = math.exp(-lam)
    k = 0
    p = rng.random()
    while p > limit:
        k += 1
        p *= rng.random()
    return k


def build(seed=SEED):
    """Return {"audience": [row, ...], "daily": [row, ...]}, each row a dict of text values."""
    rng = random.Random(seed)
    audience = []
    sizes = {}
    for seg, p in SEGMENTS.items():
        hold = int(round(p["customers"] * HOLDOUT_SHARE))
        sizes[(seg, "campaign")] = p["customers"] - hold
        sizes[(seg, "holdout")] = hold
        audience.append({"segment": seg, "grp": "campaign", "customers": str(p["customers"] - hold)})
        audience.append({"segment": seg, "grp": "holdout", "customers": str(hold)})
    daily = []
    for offset in range(DAYS):
        day = PRE_START + datetime.timedelta(days=offset)
        live = day >= CAMPAIGN_START
        for seg, p in SEGMENTS.items():
            for grp in ("campaign", "holdout"):
                rate = p["base"] * (1.0 if live else AUGUST_FACTOR)
                if live and grp == "campaign":
                    rate += p["lift"]
                orders = poisson(rng, sizes[(seg, grp)] * rate / 28)
                code_orders = 0
                revenue = 0
                code_revenue = 0
                for _ in range(orders):
                    used = live and rng.random() < (p["code"] if grp == "campaign" else LEAK)
                    value = max(150, int(round(rng.gauss(820, 250))))
                    if used:
                        code_orders += 1
                        value = int(round(value * (1 - DISCOUNT)))
                        code_revenue += value
                    revenue += value
                daily.append({"date": day.isoformat(), "segment": seg, "grp": grp, "orders": str(orders),
                              "code_orders": str(code_orders), "revenue": str(revenue),
                              "code_revenue": str(code_revenue)})
    return {"audience": audience, "daily": daily}


def write_csv(rows, fields, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_all(data, folder):
    write_csv(data["audience"], AUDIENCE_FIELDS, os.path.join(folder, "audience.csv"))
    write_csv(data["daily"], DAILY_FIELDS, os.path.join(folder, "daily.csv"))


def main():
    data = build()
    write_all(data, DATA)
    print("wrote", len(data["audience"]), "audience rows and", len(data["daily"]), "daily rows to", DATA)


if __name__ == "__main__":
    main()
