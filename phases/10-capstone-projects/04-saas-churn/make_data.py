"""Build the data for capstone 04: Shiftwren subscription and churn.

Shiftwren is a fictional staff-rota app for restaurants and clinics, sold per
location on three tiers (starter, pro, business) with monthly or annual
billing. Everything here is synthetic and deterministic (fixed seed).

Files written to data/ (see BRIEF.md for the data notes the finance team sent):

- accounts.csv: one row per account from the CRM, with some accounts twice
  (a CRM re-sync wrote a lower-case copy of the id with a trailing space).
- subscription_events.csv: the billing system's event log. event_type is
  start, change, cancel or reactivate; plan and amount are the state AFTER the
  event. Mess planted on purpose:
    * duplicate event_ids (a re-load); about a third of them carry a corrected
      amount, and the row loaded last is the right one;
    * late rows: events loaded weeks after the month they took effect in, so
      the month-end close missed them;
    * a definition change: for annual accounts, events requested before
      2026-04-01 store the annual contract value (12 x the monthly amount);
      from 2026-04-01 the billing system stores the monthly amount;
    * account ids in mixed case with stray spaces.
- finance_close.csv: the MRR and logo churn the finance team reported at each
  month-end close, computed the old way (only rows loaded by the 3rd of the
  next month, no fix for the definition change, churn counted from cancel rows).

The story planted: starter accounts on monthly billing churn far more than
the blended rate finance uses; a promotion in January to March 2026 sold many
annual plans, whose first renewal falls in January to March 2027.

    python3 make_data.py                        writes data/*.csv (seed 404)
    import make_data; make_data.build(seed=9)   returns the tables for another seed
"""
import csv
import datetime as dt
import os
import random

SEED = 404
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIRST = (2025, 1)
LAST = (2026, 9)
EXTRACT_ON = dt.date(2026, 10, 31)
SWITCH = dt.date(2026, 4, 1)
TIERS = ["starter", "pro", "business"]
PRICE = {"starter": 39, "pro": 89, "business": 189}       # EUR a location a month, monthly billing
ANNUAL = {"starter": 33, "pro": 76, "business": 161}      # EUR a location a month, annual billing
HAZARD = {"starter": 0.075, "pro": 0.030, "business": 0.012}
RENEW = {"starter": 0.62, "pro": 0.78, "business": 0.88}
FIELDS = {
    "accounts": ["account_id", "company_name", "segment", "country", "billing", "signup_date"],
    "subscription_events": ["event_id", "account_id", "event_type", "plan", "locations", "amount",
                            "requested_on", "effective_on", "loaded_on"],
    "finance_close": ["month", "reported_mrr", "reported_active_accounts", "reported_churned_accounts",
                      "reported_logo_churn_pct"],
}


def mi(year, month):
    return year * 12 + month - 1


def month_of(d):
    return mi(d.year, d.month)


def month_name(i):
    return "%04d-%02d" % (i // 12, i % 12 + 1)


def first_day(i):
    return dt.date(i // 12, i % 12 + 1, 1)


def last_day(i):
    return first_day(i + 1) - dt.timedelta(days=1)


def add_months(d, n):
    i = month_of(d) + n
    return dt.date(i // 12, i % 12 + 1, d.day)


def day_in(rng, i):
    return dt.date(i // 12, i % 12 + 1, rng.randint(1, 28))


def monthly_amount(billing, tier, locations):
    return (ANNUAL if billing == "annual" else PRICE)[tier] * locations


NAMES_A = ["Bramble", "Copper", "Harbour", "Linden", "Marigold", "Oakridge", "Saffron", "Thistle", "Willow",
           "Juniper", "Clover", "Fennel", "Hazel", "Larch", "Rowan", "Sorrel"]
NAMES_B = ["Kitchen", "Bistro", "Clinic", "Dental", "Grill", "Cafe", "Physio", "Eatery", "Surgery", "Diner"]


def simulate(rng):
    first, last = mi(*FIRST), mi(*LAST)
    accounts, events = [], []
    n = 0
    for m in range(first, last + 1):
        promo = m in (mi(2026, 1), mi(2026, 2), mi(2026, 3))
        for _ in range(int(round(rng.gauss(30 if promo else 26, 3)))):
            n += 1
            aid = "SW-%04d" % n
            signup = day_in(rng, m)
            billing = "annual" if rng.random() < (0.62 if promo else 0.2) else "monthly"
            tier = rng.choices(TIERS, weights=[50, 35, 15])[0]
            locs = 1 + int(rng.expovariate(1 / 0.9))
            locs = min(locs, 6)
            seg = "clinic" if rng.random() < 0.35 else "restaurant"
            accounts.append({"account_id": aid,
                             "company_name": "%s %s" % (rng.choice(NAMES_A), rng.choice(NAMES_B)),
                             "segment": seg, "country": rng.choice(["IE", "IE", "GB", "NL", "DE"]),
                             "billing": billing, "signup_date": signup.isoformat()})
            evs = [("start", tier, locs, signup, signup)]
            active, term_start, skip_to = True, signup, None
            for k in range(m + 1, last + 1):
                if skip_to is not None and k < skip_to:
                    continue
                if not active:
                    if billing == "monthly" and rng.random() < 0.05:
                        d = day_in(rng, k)
                        evs.append(("reactivate", tier, locs, d, d))
                        active, term_start = True, d
                    continue
                if billing == "annual":
                    if (k - month_of(term_start)) % 12 == 0:
                        p = RENEW[tier] - (0.05 if locs == 1 else 0.0)
                        if rng.random() >= p:
                            d = dt.date(k // 12, k % 12 + 1, term_start.day)
                            evs.append(("cancel", tier, locs, d, d))
                            active = False
                            continue
                    r = rng.random()
                    if r < 0.012 and tier != "business":
                        tier = TIERS[TIERS.index(tier) + 1]
                        d = day_in(rng, k)
                        evs.append(("change", tier, locs, d, d))
                    elif r < 0.02:
                        locs += 1
                        d = day_in(rng, k)
                        evs.append(("change", tier, locs, d, d))
                    continue
                tenure = k - month_of(term_start)
                h = HAZARD[tier] * (1.6 if tenure <= 2 else 1.0)
                r = rng.random()
                if r < h:
                    req = day_in(rng, k)
                    evs.append(("cancel", tier, locs, req, first_day(k + 1)))
                    active = False
                    skip_to = k + 2
                elif r < h + 0.022:
                    if tier != "business" and rng.random() < 0.6:
                        tier = TIERS[TIERS.index(tier) + 1]
                    else:
                        locs += 1
                    d = day_in(rng, k)
                    evs.append(("change", tier, locs, d, d))
                elif r < h + 0.034:
                    if locs > 1:
                        locs -= 1
                    elif tier != "starter":
                        tier = TIERS[TIERS.index(tier) - 1]
                    else:
                        continue
                    d = day_in(rng, k)
                    evs.append(("change", tier, locs, d, d))
            for etype, t, lc, req, eff in evs:
                if eff > last_day(last):
                    continue
                amt = 0 if etype == "cancel" else monthly_amount(billing, t, lc)
                if billing == "annual" and req < SWITCH:
                    amt *= 12
                events.append({"account_id": aid, "event_type": etype, "plan": t, "locations": lc,
                               "amount": amt, "requested_on": req, "effective_on": eff, "billing": billing})
    return accounts, events


def build(seed=SEED):
    """Return {"accounts": rows, "subscription_events": rows, "finance_close": rows}, values as CSV text."""
    rng = random.Random(seed)
    accounts, events = simulate(rng)
    events.sort(key=lambda e: (e["effective_on"], e["account_id"]))
    rows = []
    for i, e in enumerate(events, 1):
        loaded = e["requested_on"] + dt.timedelta(days=rng.randint(0, 2))
        if rng.random() < 0.08:
            loaded = e["effective_on"] + dt.timedelta(days=rng.randint(6, 45))
        aid = e["account_id"]
        if rng.random() < 0.04:
            aid = aid.lower() + " "
        row = {"event_id": "EV%05d" % i, "account_id": aid, "event_type": e["event_type"], "plan": e["plan"],
               "locations": e["locations"], "amount": e["amount"], "requested_on": e["requested_on"],
               "effective_on": e["effective_on"], "loaded_on": loaded, "_billing": e["billing"]}
        rows.append(row)
        if rng.random() < 0.035:
            dup = dict(row)
            dup["loaded_on"] = loaded + dt.timedelta(days=rng.randint(1, 20))
            if e["event_type"] != "cancel" and rng.random() < 0.35:
                # a correction: the first load had the location count wrong
                wrong = e["locations"] + 1
                row["locations"] = wrong
                row["amount"] = e["amount"] // e["locations"] * wrong
            rows.append(dup)
    rows = [r for r in rows if r["loaded_on"] <= EXTRACT_ON]
    close = finance_close(rows)
    acc_rows = []
    for a in accounts:
        acc_rows.append(a)
        if rng.random() < 0.025:
            b = dict(a)
            b["account_id"] = a["account_id"].lower() + " "
            acc_rows.append(b)
    rows.sort(key=lambda r: (r["loaded_on"], r["event_id"]))
    out_events = []
    for r in rows:
        out_events.append({k: (v.isoformat() if isinstance(v, dt.date) else str(v))
                           for k, v in r.items() if not k.startswith("_")})
    return {"accounts": acc_rows, "subscription_events": out_events, "finance_close": close}


def finance_close(rows):
    """The numbers finance reported, computed the old way at each month-end close."""
    out = []
    for m in range(mi(*FIRST), mi(*LAST) + 1):
        cutoff = first_day(m + 1) + dt.timedelta(days=2)
        seen = [r for r in rows if r["loaded_on"] <= cutoff and r["effective_on"] <= last_day(m)]
        state = {}
        for r in sorted(seen, key=lambda r: (r["effective_on"], r["loaded_on"])):
            state[r["account_id"].strip().upper()] = r["amount"]
        active = sum(1 for v in state.values() if v > 0)
        churned = sum(1 for r in seen if r["event_type"] == "cancel" and month_of(r["effective_on"]) == m)
        out.append({"month": month_name(m), "reported_mrr": sum(state.values()),
                    "reported_active_accounts": active, "reported_churned_accounts": churned,
                    "reported_logo_churn_pct": "%.2f" % (100.0 * churned / active if active else 0.0)})
    return out


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
