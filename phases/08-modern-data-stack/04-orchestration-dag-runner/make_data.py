"""Build the files for a synthetic nightly pipeline at an online grocery.

jobs.csv:      job, depends_on (space separated), minutes, retries
               one row per job in the nightly DAG
failures.csv:  run_date, job, attempt
               one row per attempt that failed; any attempt not listed succeeded
orders.csv:    order_date, order_id, amount
               the orders the extract_orders job loads, one day per night

The data is synthetic and deterministic (fixed seed). The pipeline runs every
night from 1 to 14 October 2026. A few attempts fail for a moment and work on
retry. On the last night the payments source is down: every attempt of
extract_payments fails.

    python3 make_data.py          writes the three files (seed 4)
    import make_data; make_data.build(seed=9)   returns the rows for another seed
"""
import csv
import datetime
import os
import random

SEED = 4
HERE = os.path.dirname(os.path.abspath(__file__))
FIELDS = {"jobs": ["job", "depends_on", "minutes", "retries"],
          "failures": ["run_date", "job", "attempt"],
          "orders": ["order_date", "order_id", "amount"]}
FIRST_NIGHT = datetime.date(2026, 10, 1)
NIGHTS = 14
HARD_FAILURE = ("2026-10-14", "extract_payments")
# job: (depends on, typical minutes, retries)
JOBS = {
    "extract_orders": ((), 6, 2),
    "extract_payments": ((), 5, 2),
    "extract_customers": ((), 3, 2),
    "stg_orders": (("extract_orders",), 3, 1),
    "stg_payments": (("extract_payments",), 3, 1),
    "stg_customers": (("extract_customers",), 2, 1),
    "fct_orders": (("stg_orders", "stg_payments"), 6, 1),
    "dim_customers": (("stg_customers",), 2, 1),
    "mart_city_revenue": (("fct_orders", "dim_customers"), 4, 1),
    "mart_customer_counts": (("dim_customers",), 2, 1),
    "dashboard_refresh": (("mart_city_revenue", "mart_customer_counts"), 5, 2),
    "finance_email": (("mart_city_revenue",), 1, 0),
}


def build(seed=SEED):
    """Return {"jobs": [...], "failures": [...], "orders": [...]}, rows of text values."""
    rng = random.Random(seed)
    jobs = []
    for name in sorted(JOBS):
        deps, minutes, retries = JOBS[name]
        jobs.append({"job": name, "depends_on": " ".join(deps),
                     "minutes": str(max(1, minutes + rng.randint(-1, 1))), "retries": str(retries)})
    failures, orders = [], []
    for i in range(NIGHTS):
        night = (FIRST_NIGHT + datetime.timedelta(days=i)).isoformat()
        for name in sorted(JOBS):
            retries = JOBS[name][2]
            if (night, name) == HARD_FAILURE:
                fails = retries + 1
            elif rng.random() < 0.06:
                fails = 2 if rng.random() < 0.3 else 1
            else:
                fails = 0
            for attempt in range(1, min(fails, retries + 1) + 1):
                failures.append({"run_date": night, "job": name, "attempt": str(attempt)})
        for _ in range(rng.randint(45, 70)):
            orders.append({"order_date": night, "order_id": str(70000 + len(orders) + 1),
                           "amount": "%.2f" % rng.uniform(150, 2500)})
    return {"jobs": jobs, "failures": failures, "orders": orders}


def write_csv(rows, path, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_all(tables, folder):
    for name in ("jobs", "failures", "orders"):
        write_csv(tables[name], os.path.join(folder, name + ".csv"), FIELDS[name])


def main():
    tables = build()
    write_all(tables, os.path.join(HERE, "data"))
    print("wrote", ", ".join("%d %s" % (len(tables[k]), k) for k in ("jobs", "failures", "orders")))


if __name__ == "__main__":
    main()
