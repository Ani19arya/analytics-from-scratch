"""Build the synthetic dataset for lesson 13.

Brindlefox, a fictional recipe app, tested five versions of its recipe page
for 14 days: the current page (A) and four challengers (B, C, D, E). Every new
visitor was meant to land in one of the five at random, 20% each.

data/daily.csv: one row per variant per day of the test:
    day        1 to 14
    variant    A, B, C, D or E
    users      new users assigned that day
    signups    of those, how many started a free trial
    saves      how many saved at least one recipe
    shares     how many shared a recipe

Built into the data (the test does not rely on these, it recomputes everything):
- B really lifts signups and D really lifts saves.
- C changes nothing; any "win" for C is noise.
- E has a logging bug: about 7% of E's users who would NOT sign up are never
  recorded, so E has too few users and its signup rate looks too good.

Run: python3 make_data.py      (writes data/daily.csv for the default seed)
Use: build(seed) returns {"daily": rows} without writing anything.
"""
import csv
import os
import random

DEFAULT_SEED = 1391
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIELDS = {"daily": ["day", "variant", "users", "signups", "saves", "shares"]}
VARIANTS = ["A", "B", "C", "D", "E"]
DAYS = 14
BASE = {"signup": 0.10, "save": 0.30, "share": 0.04}
EFFECT = {"B": {"signup": 0.03}, "D": {"save": 0.045}}
E_DROP = 0.10


def build(seed=DEFAULT_SEED):
    """Return {"daily": rows}. The same seed always gives the same rows."""
    rng = random.Random(seed)
    rows = []
    for day in range(1, DAYS + 1):
        counts = {v: [0, 0, 0, 0] for v in VARIANTS}
        arrivals = 1300 + rng.randrange(0, 200)
        for _ in range(arrivals):
            v = rng.choice(VARIANTS)
            rates = dict(BASE)
            for metric, lift in EFFECT.get(v, {}).items():
                rates[metric] += lift
            signup = rng.random() < rates["signup"]
            save = rng.random() < rates["save"] + (0.25 if signup else 0.0)
            share = rng.random() < rates["share"] + (0.04 if save else 0.0)
            if v == "E" and not signup and rng.random() < E_DROP:
                continue
            c = counts[v]
            c[0] += 1
            c[1] += signup
            c[2] += save
            c[3] += share
        for v in VARIANTS:
            c = counts[v]
            rows.append({"day": day, "variant": v, "users": c[0], "signups": c[1],
                         "saves": c[2], "shares": c[3]})
    return {"daily": rows}


def write_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_all(folder, tables):
    for name, rows in tables.items():
        write_csv(os.path.join(folder, name + ".csv"), rows, FIELDS[name])


def main():
    tables = build()
    write_all(DATA, tables)
    for name, rows in tables.items():
        print("wrote", len(rows), "rows to", os.path.join(DATA, name + ".csv"), "(synthetic)")


if __name__ == "__main__":
    main()
