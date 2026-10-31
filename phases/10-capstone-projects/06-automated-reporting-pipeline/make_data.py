"""Build the data for capstone 10-06: the Parcelwick weekly business review.

Parcelwick is a fictional parcel-locker network in Bristol: couriers drop
parcels into locker banks at five sites, customers collect them. Everything
here is synthetic and deterministic (fixed seed).

Files written to data/:

- sites.csv: the five locker sites.
- drops/parcels_YYYY-MM-DD.csv: the weekly extract the courier system drops
  every Monday at 06:00, one row per parcel outcome recorded in the seven
  days before. Mess planted on purpose:
    * late rows: about 1 row in 20 misses its week's drop and arrives in the
      next one, and parcels delivered after the promised date are recorded
      when they are delivered, so last week's numbers change;
    * first attempts: until 13 September the old courier app wrote a row for
      a failed first attempt (F) and another when the parcel was delivered
      (D); the latest outcome is the truth;
    * a definition change: from the drop of 14 September 2026 the new courier
      app writes outcomes as words (delivered, failed, returned) instead of
      codes (D, F, R), and writes only the final outcome;
    * a duplicate file: the 12 October drop was sent twice
      (parcels_2026-10-12_resend.csv is identical);
    * an outage: site PW05 (Southville) sent nothing for the week of
      19 October; its rows have not arrived yet.

    python3 make_data.py                         writes data/ (seed 606)
    import make_data; make_data.build(seed=13)   returns {"sites": rows, "drops": {file name: rows}}
"""
import csv
import datetime as dt
import os
import random
import shutil

SEED = 606
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIRST_WEEK = dt.date(2026, 7, 27)        # Monday; the first drop is a week later
LAST_DROP = dt.date(2026, 10, 26)        # Monday
SWITCH = dt.date(2026, 9, 14)            # first drop written by the new courier app
OUTAGE = ("PW05", dt.date(2026, 10, 19))  # site and week (Monday) with no rows yet
RESEND = dt.date(2026, 10, 12)
SITES = [
    # site_id, name, lockers, parcels a week, on-time chance
    ("PW01", "Clifton", 120, 42, 0.93),
    ("PW02", "Bedminster", 90, 38, 0.92),
    ("PW03", "Redland", 80, 30, 0.94),
    ("PW04", "Easton", 100, 36, 0.91),
    ("PW05", "Southville", 70, 28, 0.93),
]
FIELDS = ["parcel_id", "site_id", "promised_date", "outcome", "outcome_date", "fee_gbp"]
NEW_CODE = {"D": "delivered", "F": "failed", "R": "returned"}


def build(seed=SEED):
    """Return {"sites": rows, "drops": {file name: rows}}, values as text."""
    rng = random.Random(seed)
    records = []   # (recorded_drop, row)
    n = 0
    week = FIRST_WEEK
    drops = []
    d = FIRST_WEEK + dt.timedelta(days=7)
    while d <= LAST_DROP:
        drops.append(d)
        d += dt.timedelta(days=7)
    while week + dt.timedelta(days=7) <= LAST_DROP:
        for sid, _, _, per_week, p_on_time in SITES:
            if sid == "PW02" and week >= dt.date(2026, 9, 21):
                p_on_time = 0.78    # Bedminster: new courier contract from 21 September
            for _ in range(max(0, int(round(rng.gauss(per_week, 4))))):
                n += 1
                pid = "P%06d" % n
                promised = week + dt.timedelta(days=rng.randint(0, 6))
                fee = rng.choice(["2.49", "2.99", "3.49", "3.99"])
                r = rng.random()
                events = []
                if r < 0.03:
                    events.append(("F", promised))
                    events.append(("R", promised + dt.timedelta(days=rng.randint(5, 7))))
                elif r < 0.06:
                    events.append(("F", promised))
                    events.append(("F", promised + dt.timedelta(days=2)))
                elif rng.random() < p_on_time:
                    if rng.random() < 0.06:
                        events.append(("F", promised - dt.timedelta(days=1)))
                        events.append(("D", promised))
                    else:
                        events.append(("D", promised - dt.timedelta(days=rng.choice([0, 0, 0, 1]))))
                else:
                    if rng.random() < 0.5:
                        events.append(("F", promised))
                    events.append(("D", promised + dt.timedelta(days=rng.randint(1, 3))))
                for code, when in events:
                    drop = when - dt.timedelta(days=when.weekday()) + dt.timedelta(days=7)
                    if rng.random() < 0.05:
                        drop += dt.timedelta(days=7)
                    if sid == OUTAGE[0] and OUTAGE[1] <= when <= OUTAGE[1] + dt.timedelta(days=6):
                        continue    # the site's sync failed; these rows have not arrived yet
                    if drop > LAST_DROP:
                        continue
                    if drop >= SWITCH and (code, when) != events[-1]:
                        continue    # the new app writes only the final outcome
                    out = NEW_CODE[code] if drop >= SWITCH else code
                    records.append((drop, {"parcel_id": pid, "site_id": sid, "promised_date": promised.isoformat(),
                                           "outcome": out, "outcome_date": when.isoformat(),
                                           "fee_gbp": fee if code == "D" else "0.00"}))
        week += dt.timedelta(days=7)
    files = {}
    for d in drops:
        rows = [r for drop, r in records if drop == d]
        rows.sort(key=lambda r: (r["outcome_date"], r["parcel_id"]))
        files["parcels_%s.csv" % d.isoformat()] = rows
    files["parcels_%s_resend.csv" % RESEND.isoformat()] = [dict(r) for r in files["parcels_%s.csv" % RESEND.isoformat()]]
    sites = [{"site_id": s[0], "site_name": s[1], "lockers": str(s[2])} for s in SITES]
    return {"sites": sites, "drops": files}


def write_csv(rows, path, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in fields})


def write_all(tables, folder):
    """Write sites.csv and drops/*.csv under folder (the drops folder is rebuilt from scratch)."""
    write_csv(tables["sites"], os.path.join(folder, "sites.csv"), ["site_id", "site_name", "lockers"])
    drops = os.path.join(folder, "drops")
    if os.path.isdir(drops):
        shutil.rmtree(drops)
    for name, rows in sorted(tables["drops"].items()):
        write_csv(rows, os.path.join(drops, name), FIELDS)


if __name__ == "__main__":
    t = build()
    write_all(t, DATA)
    print("data/sites.csv: %d rows" % len(t["sites"]))
    for name, rows in sorted(t["drops"].items()):
        print("data/drops/%s: %d rows" % (name, len(rows)))
