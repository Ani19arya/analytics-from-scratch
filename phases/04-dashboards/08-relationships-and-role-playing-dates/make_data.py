"""Build the synthetic orders, date and campaign tables for this lesson.

Run from the lesson folder: python3 make_data.py
Writes four files to data/:
  dim_date.csv        one row per day, 1 January to 31 July 2026
  orders.csv          one row per order placed January to June 2026, with an
                      order date and a ship date. Orders placed in the last days
                      of June have not shipped yet, so their ship_date is blank.
  campaigns.csv       one row per marketing campaign
  order_campaign.csv  the bridge: one row per (order, campaign) the order was
                      touched by. An order can have zero, one or several
                      campaigns, and the export repeats a few pairs.
The data is synthetic and deterministic (fixed seed).

The test calls build(seed=...) with another seed to get a second,
different dataset in memory, so a query that hard-codes the answers fails.
"""
import csv
import datetime
import os
import random

DEFAULT_SEED = 408

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CAMPAIGNS = [(1, "Instagram"), (2, "Referral"), (3, "Search ads"), (4, "Spring email")]
FIRST, LAST_ORDER, LAST_DAY = datetime.date(2026, 1, 1), datetime.date(2026, 6, 30), datetime.date(2026, 7, 31)


def build(seed=DEFAULT_SEED):
    """Return {"dim_date": [...], "orders": [...], "campaigns": [...], "order_campaign": [...]}
    with values as they appear in the CSV files (a blank ship_date is "")."""
    rng = random.Random(seed)
    dim_date = []
    day = FIRST
    while day <= LAST_DAY:
        dim_date.append({"date": day.isoformat(), "year_month": day.isoformat()[:7]})
        day += datetime.timedelta(days=1)

    orders, bridge = [], []
    order_id = 1000
    day = FIRST
    while day <= LAST_ORDER:
        for _ in range(rng.randint(1, 3)):
            order_id += 1
            ship = day + datetime.timedelta(days=rng.choice([0, 1, 2, 2, 3, 4, 5, 7, 9]))
            if (LAST_ORDER - day).days < 4 and rng.random() < 0.7:
                ship_text = ""          # not shipped yet when the export ran
            else:
                ship_text = ship.isoformat()
            orders.append({"order_id": order_id, "order_date": day.isoformat(), "ship_date": ship_text,
                           "amount": "%.2f" % round(rng.uniform(18, 260), 2)})
            touched = rng.choice([0, 0, 1, 1, 1, 2, 2, 3])
            for campaign_id in sorted(rng.sample([c[0] for c in CAMPAIGNS], touched)):
                bridge.append({"order_id": order_id, "campaign_id": campaign_id})
                if rng.random() < 0.02:  # the export repeats a few pairs
                    bridge.append({"order_id": order_id, "campaign_id": campaign_id})
        day += datetime.timedelta(days=1)
    campaigns = [{"campaign_id": cid, "campaign_name": name} for cid, name in CAMPAIGNS]
    return {"dim_date": dim_date, "orders": orders, "campaigns": campaigns, "order_campaign": bridge}


def main():
    os.makedirs(DATA, exist_ok=True)
    for name, rows in build().items():
        with open(os.path.join(DATA, name + ".csv"), "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print("wrote %d rows to data/%s.csv" % (len(rows), name))


if __name__ == "__main__":
    main()
