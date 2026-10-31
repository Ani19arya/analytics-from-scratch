"""Build the synthetic storage metadata and query log for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/blocks.csv and data/queries.csv. Everything is synthetic and
deterministic (fixed seed). Brightcart is a fictional online grocery, and the
warehouse here is a model of how a cloud warehouse stores a table, not a real
product's internals.

- blocks.csv: the table app_events (1 August to 31 October 2026) as the
  warehouse stores it. It is partitioned by event_date (one partition per day)
  and, inside each day, cut into blocks sorted by store_id (clustered), so each
  block covers a narrow range of stores. One row per block: the day, the block
  number, its row count, the smallest and largest store_id in it, and the
  bytes each column takes in that block (the storage is columnar: each
  column is stored, and read, on its own).
- queries.csv: the warehouse's query log for October, one row per dashboard
  tile: the SQL, the columns it reads, the event_date range its WHERE clause
  restricts (blank when it restricts none), whether that filter is written
  directly on event_date (prunable = 1) or on something else, the store it
  filters on (blank when none), and how many times it ran in October.

build(seed) returns both tables without writing anything. The test calls it
with a second seed: block sizes, store ranges and run counts all change.
"""
import csv
import datetime
import os
import random

SEED = 805
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
START = datetime.date(2026, 8, 1)
DAYS = 92
BLOCKS_PER_DAY = 8
STORES = 40
# Average bytes per row of each column (payload is a JSON blob of the full event).
WIDTH = {"event_date": 4, "event_id": 8, "event_time": 8, "store_id": 4, "user_id": 8, "event_type": 9, "amount": 8, "payload": 1150}
COLUMNS = list(WIDTH)

QUERIES = [
    # dashboard, tile, sql, columns, date_from, date_to, prunable, store_id, runs per day (October)
    ("Store live ops", "Orders today by store",
     "SELECT * FROM app_events WHERE DATE(event_time) = '2026-10-31'",
     COLUMNS, "2026-10-31", "2026-10-31", 0, "", 12),
    ("Store live ops", "Latest 100 events",
     "SELECT * FROM app_events ORDER BY event_time DESC LIMIT 100",
     COLUMNS, "", "", 0, "", 1),
    ("Store live ops", "Store 17 basket sizes",
     "SELECT store_id, event_type, amount FROM app_events WHERE event_date BETWEEN '2026-10-25' AND '2026-10-31' AND store_id = 17",
     ["store_id", "event_type", "amount"], "2026-10-25", "2026-10-31", 1, "17", 12),
    ("Weekly finance", "Revenue last 7 days",
     "SELECT event_date, event_type, amount FROM app_events WHERE event_date BETWEEN '2026-10-25' AND '2026-10-31'",
     ["event_date", "event_type", "amount"], "2026-10-25", "2026-10-31", 1, "", 1),
    ("Marketing", "Active users last 30 days",
     "SELECT COUNT(DISTINCT user_id) FROM app_events WHERE event_date BETWEEN '2026-10-02' AND '2026-10-31' AND event_type = 'visit'",
     ["user_id", "event_type"], "2026-10-02", "2026-10-31", 1, "", 4),
    ("Marketing", "Store 5 visitors by day",
     "SELECT event_date, COUNT(DISTINCT user_id) FROM app_events WHERE event_date >= '2026-08-01' AND store_id = 5 GROUP BY event_date",
     ["event_date", "user_id", "store_id"], "2026-08-01", "2026-10-31", 1, "5", 2),
]


def build(seed=SEED):
    """Return {"blocks": [...], "queries": [...]}, rows as dicts of text, like the CSV files."""
    rng = random.Random(seed)
    blocks = []
    for d in range(DAYS):
        day = (START + datetime.timedelta(days=d)).isoformat()
        cuts = sorted(rng.sample(range(2, STORES + 1), BLOCKS_PER_DAY - 1))
        lows = [1] + cuts
        highs = [c for c in cuts] + [STORES]  # neighbouring blocks share their boundary store
        growth = 1 + 0.004 * d
        for b in range(BLOCKS_PER_DAY):
            rows = int(rng.randint(180000, 260000) * growth)
            row = {"event_date": day, "block_id": b + 1, "rows": rows,
                   "min_store": lows[b], "max_store": highs[b]}
            for col in COLUMNS:
                row["bytes_" + col] = int(rows * WIDTH[col] * rng.uniform(0.9, 1.1))
            blocks.append(row)
    queries = []
    for k, (dash, tile, sql, cols, lo, hi, prunable, store, per_day) in enumerate(QUERIES, 1):
        runs = per_day * 31 if seed == SEED else rng.randint(1, 30) * 31
        queries.append({"query_id": "q%d" % k, "dashboard": dash, "tile": tile, "sql": sql,
                        "columns": ";".join(cols), "date_from": lo, "date_to": hi,
                        "prunable": prunable, "store_id": store, "runs": runs})
    return {"blocks": blocks, "queries": queries}


def write(name, rows):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/%s" % (len(rows), name))


def main():
    os.makedirs(DATA, exist_ok=True)
    tables = build()
    write("blocks.csv", tables["blocks"])
    write("queries.csv", tables["queries"])


if __name__ == "__main__":
    main()
