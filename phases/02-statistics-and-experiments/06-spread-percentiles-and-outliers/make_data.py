"""Build data/salaries.csv: a synthetic pay survey of 240 analysts for the
fictional recruiting firm Brightline Talent.

Columns: response_id, title, years_experience, base_pay (yearly, in dollars, as typed).
Most rows are ordinary analysts. A few are lead analysts with long experience and
high pay, and they are real. A few respondents typed their pay in thousands
(82 instead of 82,000), which is a data entry error.
The data is synthetic. No row is a real person.

Run: python3 make_data.py          (writes data/salaries.csv for the default seed)
Use: build(seed) returns {"salaries": [row dicts]} without writing anything.
"""
import csv
import math
import os
import random

DEFAULT_SEED = 606
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "salaries.csv")
FIELDS = ["response_id", "title", "years_experience", "base_pay"]
# title: (share of respondents, median pay, spread on the log scale, years range)
TITLES = [("Data Analyst", 0.45, 72000, 0.16, (0, 5)),
          ("Business Analyst", 0.30, 76000, 0.16, (1, 7)),
          ("Senior Data Analyst", 0.22, 98000, 0.13, (4, 10))]
ROWS = 240
LEADS = 6
TYPED_IN_THOUSANDS = 3


def build(seed=DEFAULT_SEED):
    """Return {"salaries": rows}. The same seed always gives the same rows."""
    rng = random.Random(seed)
    rows = []
    weights = [t[1] for t in TITLES]
    for i in range(1, ROWS - LEADS + 1):
        title, _, median, spread, (lo, hi) = rng.choices(TITLES, weights=weights)[0]
        pay = round(rng.lognormvariate(math.log(median), spread) / 500) * 500
        rows.append({"response_id": i, "title": title, "years_experience": rng.randint(lo, hi),
                     "base_pay": pay})
    for i in range(ROWS - LEADS + 1, ROWS + 1):
        rows.append({"response_id": i, "title": "Lead Analyst", "years_experience": rng.randint(10, 18),
                     "base_pay": round(rng.uniform(165000, 240000) / 500) * 500})
    for row in rng.sample(rows[:ROWS - LEADS], TYPED_IN_THOUSANDS):
        row["base_pay"] = round(row["base_pay"] / 1000)
    rng.shuffle(rows)
    for new_id, row in enumerate(rows, 1):
        row["response_id"] = new_id
    return {"salaries": rows}


def write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    rows = build()["salaries"]
    write_csv(OUT, rows)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
