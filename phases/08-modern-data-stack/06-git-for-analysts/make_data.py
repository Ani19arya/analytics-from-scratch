"""Build the synthetic orders table and the recorded commit history for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/orders.csv, data/commits.csv and data/file_versions.csv.
Everything is synthetic and deterministic (fixed seed). Nothing here was
recorded from a real repository; the history is written the way git would
record it, so you can study it without git installed.

- orders.csv: Brightcart orders from September and October 2026.
  status is delivered, refunded, cancelled or pending. discount is money
  taken off the price. is_test is 1 for internal test orders.
- commits.csv: one row per commit, oldest first. parent_id is the commit
  before it (empty for the first commit).
- file_versions.csv: for every commit, the full text of each file that
  commit created or changed, one row per line. A file a commit did not touch
  is the same as in the parent commit.

The story built into the history: someone edits the revenue query so that
orders that should not count as revenue start counting. Later, someone else
makes a correct change (revenue net of discounts) and a cosmetic one.

build(seed) returns the rows without writing anything. The test calls it with
a second seed: the authors, commit ids, order of commits, the exact bad edit
and the orders all change.
"""
import csv
import datetime
import os
import random

SEED = 809
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
AUTHORS = ["Asha", "Ravi", "Leena", "Omar"]

REVENUE_V1 = [
    "-- Monthly revenue for the finance dashboard.",
    "-- One row per calendar month.",
    "SELECT",
    "  strftime('%Y-%m', order_date) AS month,",
    "  ROUND(SUM(amount), 2) AS revenue",
    "FROM orders",
    "WHERE is_test = 0",
    "  AND status = 'delivered'",
    "GROUP BY month",
    "ORDER BY month;",
]
CITY_V1 = [
    "-- Orders per month for the operations review.",
    "SELECT strftime('%Y-%m', order_date) AS month, COUNT(*) AS orders",
    "FROM orders",
    "WHERE is_test = 0",
    "GROUP BY month",
    "ORDER BY month;",
]
README_V1 = [
    "# Brightcart analytics queries",
    "Each .sql file feeds one dashboard tile.",
    "Change a query in a commit of its own, with a message that says why.",
]
BAD_EDITS = [
    ("  AND status IN ('delivered', 'refunded')", "Count refunded orders as revenue too"),
    ("  AND status <> 'cancelled'", "Only cancelled orders are not revenue"),
]


def replace_line(old, new):
    def change(lines):
        assert old in lines, old
        return [new if x == old else x for x in lines]
    return change


def insert_after(anchor, new):
    def change(lines):
        i = lines.index(anchor)
        return lines[:i + 1] + [new] + lines[i + 1:]
    return change


def build_orders(rng):
    rows = []
    day = datetime.date(2026, 9, 1)
    oid = 1
    while day <= datetime.date(2026, 10, 31):
        for _ in range(rng.randint(4, 9)):
            status = rng.choices(["delivered", "refunded", "cancelled", "pending"], [82, 7, 8, 3])[0]
            amount = round(rng.uniform(18, 140), 2)
            discount = rng.choice([0.0] * 7 + [5.0, 10.0, round(amount * 0.15, 2)])
            is_test = 1 if rng.random() < 0.03 else 0
            rows.append({"order_id": oid, "order_date": day.isoformat(), "status": status,
                         "amount": amount, "discount": discount, "is_test": is_test})
            oid += 1
        day += datetime.timedelta(days=1)
    return rows


def plan(rng):
    """The steps of the history, in commit order. Each step: (path, change, message)."""
    bad_line, bad_message = rng.choice(BAD_EDITS)
    revenue_steps = [
        ("revenue.sql", lambda _: list(REVENUE_V1), "Add the monthly revenue query"),
        ("revenue.sql", replace_line("  AND status = 'delivered'", bad_line), bad_message),
        ("revenue.sql", replace_line("  ROUND(SUM(amount), 2) AS revenue", "  ROUND(SUM(amount - discount), 2) AS revenue"),
         "Revenue is net of discounts, as finance defines it"),
        ("revenue.sql", replace_line(REVENUE_V1[0], "-- Monthly revenue for the finance dashboard. Owner: analytics."),
         "Say who owns the revenue query"),
    ]
    other_steps = [
        ("orders_by_month.sql", lambda _: list(CITY_V1), "Add orders per month for operations"),
        ("orders_by_month.sql", insert_after("WHERE is_test = 0", "  AND status <> 'cancelled'"),
         "Operations counts only orders that were not cancelled"),
        ("README.md", lambda _: list(README_V1), "Add a README for the query folder"),
    ]
    # Keep the order inside each list, interleave the two lists at random.
    # The first commit always creates revenue.sql.
    steps, a, b = [revenue_steps[0]], 1, 0
    while a < len(revenue_steps) or b < len(other_steps):
        take_revenue = b == len(other_steps) or (a < len(revenue_steps) and rng.random() < 0.5)
        if take_revenue:
            steps.append(revenue_steps[a])
            a += 1
        else:
            steps.append(other_steps[b])
            b += 1
    return steps


def build(seed=SEED):
    """Return {"orders": [...], "commits": [...], "file_versions": [...]}, rows as dicts."""
    rng = random.Random(seed)
    orders = build_orders(rng)
    files, commits, versions = {}, [], []
    when = datetime.datetime(2026, 9, 7, 10, 0, 0)
    parent = ""
    used = set()
    steps = plan(rng)
    # The four revenue.sql commits are by four different people, so blame tells them apart.
    revenue_authors = iter(rng.sample(AUTHORS, 4))
    for path, change, message in steps:
        cid = "%07x" % rng.randrange(16 ** 7)
        while cid in used:
            cid = "%07x" % rng.randrange(16 ** 7)
        used.add(cid)
        when += datetime.timedelta(days=rng.randint(2, 6), minutes=rng.randint(0, 600))
        files[path] = change(files.get(path))
        commits.append({"commit_id": cid, "parent_id": parent, "author": next(revenue_authors) if path == "revenue.sql" else rng.choice(AUTHORS),
                        "committed_at": when.strftime("%Y-%m-%d %H:%M:%S"), "message": message})
        for n, line in enumerate(files[path], 1):
            versions.append({"commit_id": cid, "path": path, "line_no": n, "line": line})
        parent = cid
    return {"orders": orders, "commits": commits, "file_versions": versions}


def write(name, rows):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/%s" % (len(rows), name))


def main():
    os.makedirs(DATA, exist_ok=True)
    tables = build()
    write("orders.csv", tables["orders"])
    write("commits.csv", tables["commits"])
    write("file_versions.csv", tables["file_versions"])


if __name__ == "__main__":
    main()
