"""Build the data for capstone 10-05: the Kettlemoor executive dashboard.

Kettlemoor is a fictional chain of bakery-cafes in Yorkshire with four shops.
Everything here is synthetic and deterministic (fixed seed).

Files written to data/ (see BRIEF.md for the notes the data team sent):

- daily_sales.csv: one row per shop and trading day as the till system sent
  it, 1 September 2025 to 30 September 2026. Mess planted on purpose:
    * re-sent days: a shop's day sent again later (loaded_at is later); about
      a third of re-sends carry corrected numbers after the till count, and
      the row loaded last is the right one;
    * a definition change: until 30 June 2026 gross_sales is before
      discounts; from 1 July 2026 the new till software reports gross_sales
      already net of discounts (the discounts column is still filled in);
    * one missing day: the York shop's 14 September 2026 never arrived.
- stores.csv: the four shops and their opening dates (Ripon opened 2 March 2026).
- store_closures.csv: days a shop was shut (Leeds closed for a refit in
  September 2025).
- targets.csv: the monthly net revenue target per shop for 2026.

    python3 make_data.py                         writes data/*.csv (seed 505)
    import make_data; make_data.build(seed=11)   returns the tables for another seed
"""
import csv
import datetime as dt
import math
import os
import random

SEED = 505
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIRST = dt.date(2025, 9, 1)
LAST = dt.date(2026, 9, 30)
SWITCH = dt.date(2026, 7, 1)
STORES = [
    # store_id, name, city, opened_on, base orders a day, yearly growth, cogs share of net revenue
    ("KM01", "Kettlemoor York", "York", "2019-04-06", 410, 0.05, 0.300),
    ("KM02", "Kettlemoor Harrogate", "Harrogate", "2021-08-14", 300, -0.03, 0.315),
    ("KM03", "Kettlemoor Leeds", "Leeds", "2023-03-11", 280, 0.07, 0.305),
    ("KM04", "Kettlemoor Ripon", "Ripon", "2026-03-02", 170, 0.0, 0.330),
]
CLOSURES = [("KM03", "2025-09-08", "2025-09-14", "refit")]
MISSING = [("KM01", "2026-09-14")]
SEASON = {1: 0.86, 2: 0.9, 3: 0.97, 4: 1.0, 5: 1.02, 6: 1.04, 7: 1.08, 8: 1.1, 9: 1.0, 10: 0.98, 11: 1.0, 12: 1.18}
FIELDS = {
    "daily_sales": ["sales_date", "store_id", "orders", "gross_sales", "discounts", "cogs", "loaded_at"],
    "stores": ["store_id", "store_name", "city", "opened_on"],
    "store_closures": ["store_id", "closed_from", "closed_to", "reason"],
    "targets": ["month", "store_id", "revenue_target"],
}


def days(a, b):
    d = a
    while d <= b:
        yield d
        d += dt.timedelta(days=1)


def closed(store_id, d, closures):
    return any(s == store_id and dt.date.fromisoformat(a) <= d <= dt.date.fromisoformat(b) for s, a, b, _ in closures)


def money(x):
    return "%.2f" % x


def build(seed=SEED):
    """Return {"daily_sales", "stores", "store_closures", "targets"}: lists of dicts of text."""
    rng = random.Random(seed)
    sales = []
    for sid, _, _, opened, base, growth, cogs_share in STORES:
        opened_d = dt.date.fromisoformat(opened)
        for d in days(FIRST, LAST):
            if d < opened_d or closed(sid, d, CLOSURES):
                continue
            years = (d - FIRST).days / 365.0
            ramp = 1.0 if (d - opened_d).days > 120 else 0.7 + 0.3 * (d - opened_d).days / 120.0
            mean = base * SEASON[d.month] * (1 + growth) ** years * ramp * (1.22 if d.weekday() >= 5 else 1.0)
            orders = max(0, int(round(rng.gauss(mean, math.sqrt(mean) * 1.5))))
            basket = rng.gauss(8.10 if d.weekday() >= 5 else 7.60, 0.25)
            net = orders * basket
            disc_share = rng.uniform(0.04, 0.08)
            gross_before = net / (1 - disc_share)
            discounts = gross_before - net
            gross = net if d >= SWITCH else gross_before
            share = cogs_share + (0.03 if sid == "KM02" and d >= dt.date(2026, 4, 1) else 0.0)
            cogs = net * rng.gauss(share, 0.01)
            if (sid, d.isoformat()) in MISSING:
                continue
            loaded = dt.datetime.combine(d + dt.timedelta(days=1), dt.time(2, rng.randint(0, 59)))
            row = {"sales_date": d.isoformat(), "store_id": sid, "orders": str(orders), "gross_sales": money(gross),
                   "discounts": money(discounts), "cogs": money(cogs), "loaded_at": loaded.isoformat(sep=" ")}
            if rng.random() < 0.03:
                again = dict(row)
                again["loaded_at"] = (loaded + dt.timedelta(days=rng.randint(1, 6), hours=rng.randint(0, 5))).isoformat(sep=" ")
                if rng.random() < 0.4:
                    # the first send was before the till count: orders and sales were off
                    k = rng.choice([0.9, 0.95, 1.05, 1.1])
                    row["orders"] = str(int(round(orders * k)))
                    row["gross_sales"] = money(gross * k)
                    row["discounts"] = money(discounts * k)
                    row["cogs"] = money(cogs * k)
                sales.append(row)
                sales.append(again)
            else:
                sales.append(row)
    sales.sort(key=lambda r: (r["loaded_at"], r["store_id"]))
    targets = []
    for month in range(1, 13):
        start = dt.date(2026, month, 1)
        end = dt.date(2026 + month // 12, month % 12 + 1, 1) - dt.timedelta(days=1)
        for sid, _, _, opened, base, growth, _ in STORES:
            opened_d = dt.date.fromisoformat(opened)
            if opened_d > start + dt.timedelta(days=27):
                continue
            plan = 0.0
            for d in days(max(start, opened_d), end):
                years = (d - FIRST).days / 365.0
                ramp = 1.0 if (d - opened_d).days > 120 else 0.7 + 0.3 * (d - opened_d).days / 120.0
                # the plan assumed at least 3% growth a year everywhere
                plan += base * SEASON[d.month] * (1 + max(growth, 0.03)) ** years * ramp * (1.22 if d.weekday() >= 5 else 1.0)
            target = plan * 7.75 * rng.uniform(1.0, 1.04)
            targets.append({"month": "2026-%02d" % month, "store_id": sid, "revenue_target": str(int(round(target, -2)))})
    stores = [{"store_id": s[0], "store_name": s[1], "city": s[2], "opened_on": s[3]} for s in STORES]
    closures = [{"store_id": s, "closed_from": a, "closed_to": b, "reason": r} for s, a, b, r in CLOSURES]
    return {"daily_sales": sales, "stores": stores, "store_closures": closures, "targets": targets}


def write_csv(rows, path, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in fields})


def write_all(tables, folder):
    for name, rows in tables.items():
        write_csv(rows, os.path.join(folder, name + ".csv"), FIELDS[name])


if __name__ == "__main__":
    t = build()
    write_all(t, DATA)
    for name, rows in t.items():
        print("data/%s.csv: %d rows" % (name, len(rows)))
