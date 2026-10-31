"""Build the data for capstone 10-03: Brambletoe marketing attribution.

Brambletoe is a fictional online shop for running shoes and kit in India,
selling in rupees. It plans in 13-week quarters; Q3 2026 is the 13 weeks that
start on Monday 29 June 2026 (29 June to 27 September). The data is synthetic
and deterministic (fixed seed). It is the raw export of 12 October 2026:

data/spend.csv        one row per week and channel: week_start, channel, spend.
data/touchpoints.csv  one row per ad or email touch: user_id, touch_time, channel.
data/orders.csv       one row per order event: order_id, user_id, order_time,
                      revenue, loaded_at.
data/display_test.csv the display holdout test: user_id, grp ("exposed" or
                      "holdout"), randomised 50/50, 3 to 30 August 2026.

The mess planted in it:
- Duplicates: the spend export overlapped, so two weeks appear twice; the
  order pixel sometimes fires twice for one order (same order_id).
- Late rows: some orders load days after they happen; orders from just
  outside Q3 are in the file too.
- A definition change halfway: from the week of 17 August 2026 the display
  agency reports spend INCLUDING its 15% fee; before that, display spend
  EXCLUDES the fee. Finance counts spend including the fee.
- Touches after the order (post-purchase emails) and touches older than the
  30-day lookback window.

The story in it: display ads reach people who were about to buy anyway, so
attribution gives display much more credit than it earns; the holdout test
shows it. Paid search and paid social bring more extra orders per rupee.

    python3 make_data.py                           writes the four CSVs (seed 3003)
    import make_data; make_data.build(seed=21)     returns the rows for another seed
"""
import csv
import datetime
import os
import random

SEED = 3003
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
Q_START = datetime.datetime(2026, 6, 29)
WEEKS = [Q_START + datetime.timedelta(days=7 * i) for i in range(13)]
FEE_CHANGE = datetime.datetime(2026, 8, 17)
FEE = 0.15
TEST_START, TEST_END = datetime.datetime(2026, 8, 3), datetime.datetime(2026, 8, 30, 23, 59)
EXPORT = datetime.datetime(2026, 10, 12)
PAID = ("paid_search", "paid_social", "display")
BASE_SPEND = {"paid_search": 60000, "paid_social": 45000, "display": 70000, "email": 8000}
# true extra orders per week = A x sqrt(weekly spend including fee)
A = {"paid_search": 0.06, "paid_social": 0.05, "display": 0.015}
BASELINE_ORDERS = 20  # per week, orders that would happen with no marketing
SPEND_FIELDS = ["week_start", "channel", "spend"]
TOUCH_FIELDS = ["user_id", "touch_time", "channel"]
ORDER_FIELDS = ["order_id", "user_id", "order_time", "revenue", "loaded_at"]
TEST_FIELDS = ["user_id", "grp"]


def poisson(rng, lam):
    limit, k, p = pow(2.718281828459045, -lam), 0, 1.0
    while True:
        p *= rng.random()
        if p < limit:
            return k
        k += 1


def fmt(t):
    return t.strftime("%Y-%m-%d %H:%M")


def build(seed=SEED):
    """Return {"spend", "touchpoints", "orders", "display_test"}, each a list of dicts of text values."""
    rng = random.Random(seed)
    spend, touches, orders, test = [], [], [], []
    state = {"orders": 0, "users": 0}

    def before(t, lo_days, hi_days):
        return t - datetime.timedelta(minutes=rng.randint(int(lo_days * 1440), int(hi_days * 1440)))

    def new_order(t, path, uid=None):
        if uid is None:
            state["users"] += 1
            uid = "B%05d" % state["users"]
        state["orders"] += 1
        oid = "O%05d" % state["orders"]
        for tt, ch in path:
            touches.append({"user_id": uid, "touch_time": fmt(tt), "channel": ch})
        if rng.random() < 0.3:  # post-purchase email: after the order, never a cause
            touches.append({"user_id": uid, "touch_time": fmt(t + datetime.timedelta(hours=rng.randint(2, 72))),
                            "channel": "email"})
        if rng.random() < 0.1:  # an old touch outside the 30-day window
            touches.append({"user_id": uid, "touch_time": fmt(before(t, 31, 45)), "channel": rng.choice(PAID)})
        lag = rng.randint(1, 18) if rng.random() < 0.06 else 0
        loaded = t + datetime.timedelta(days=lag, hours=rng.randint(0, 6))
        row = {"order_id": oid, "user_id": uid, "order_time": fmt(t),
               "revenue": "%d" % (rng.randint(18, 90) * 100), "loaded_at": fmt(loaded)}
        if loaded <= EXPORT:
            orders.append(row)
            if rng.random() < 0.04:  # the pixel fired twice
                orders.append(dict(row, loaded_at=fmt(loaded + datetime.timedelta(minutes=rng.randint(1, 90)))))

    def random_time(week):
        return week + datetime.timedelta(minutes=rng.randint(0, 7 * 1440 - 1))

    def baseline_path(t):
        path = []
        if rng.random() < 0.55:
            path.append((before(t, 0, 2), "display"))  # retargeting someone already on the way to buy
        if rng.random() < 0.25:
            path.append((before(t, 0, 5), "email"))
        if rng.random() < 0.2:
            path.append((before(t, 0, 1), "paid_search"))  # searching for the brand name
        if rng.random() < 0.15:
            path.append((before(t, 5, 25), "paid_social"))
        return path

    weeks = [Q_START - datetime.timedelta(days=7)] + WEEKS + [WEEKS[-1] + datetime.timedelta(days=7)]
    for week in weeks:
        in_q = Q_START <= week <= WEEKS[-1]
        gross = {}
        for ch, base in BASE_SPEND.items():
            g = base if ch == "email" else round(base * rng.uniform(0.55, 1.45), -2)
            gross[ch] = g
            if in_q:
                stored = g if (ch != "display" or week >= FEE_CHANGE) else round(g / (1 + FEE), 2)
                spend.append({"week_start": week.strftime("%Y-%m-%d"), "channel": ch, "spend": "%.2f" % stored})
        for ch in PAID:
            for _ in range(poisson(rng, A[ch] * gross[ch] ** 0.5)):
                t = random_time(week)
                path = [(before(t, 0, 3), ch)]
                if rng.random() < 0.5:
                    path.append((before(t, 4, 28), rng.choice([c for c in PAID if c != ch] + ["email"])))
                if ch != "display" and rng.random() < 0.3:
                    path.append((before(t, 0, 0.5), "display"))
                new_order(t, path)
        for _ in range(poisson(rng, 3)):
            t = random_time(week)
            new_order(t, [(before(t, 0, 2), "email")])
        for _ in range(poisson(rng, BASELINE_ORDERS)):
            t = random_time(week)
            new_order(t, baseline_path(t))

    window = int((TEST_END - TEST_START).total_seconds() // 60)
    for i in range(1800):
        uid = "T%04d" % (i + 1)
        grp = "exposed" if rng.random() < 0.5 else "holdout"
        test.append({"user_id": uid, "grp": grp})
        t = TEST_START + datetime.timedelta(minutes=rng.randint(0, window))
        if grp == "exposed" and rng.random() < 0.022:
            new_order(t, [(before(t, 0, 3), "display")], uid)
        elif rng.random() < 0.055:
            path = [p for p in baseline_path(t) if grp == "exposed" or p[1] != "display"]
            new_order(t, path, uid)

    spend_out = []
    for r in spend:
        spend_out.append(r)
        if r["week_start"] in ("2026-07-27", "2026-08-03"):
            spend_out.append(dict(r))  # the two exports overlapped on these weeks
    touches.sort(key=lambda r: (r["touch_time"], r["user_id"], r["channel"]))
    orders.sort(key=lambda r: (r["loaded_at"], r["order_id"]))
    return {"spend": spend_out, "touchpoints": touches, "orders": orders, "display_test": test}


def write_csv(rows, fields, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_all(data, folder):
    write_csv(data["spend"], SPEND_FIELDS, os.path.join(folder, "spend.csv"))
    write_csv(data["touchpoints"], TOUCH_FIELDS, os.path.join(folder, "touchpoints.csv"))
    write_csv(data["orders"], ORDER_FIELDS, os.path.join(folder, "orders.csv"))
    write_csv(data["display_test"], TEST_FIELDS, os.path.join(folder, "display_test.csv"))


def main():
    data = build()
    write_all(data, DATA)
    print("wrote", ", ".join("%d %s rows" % (len(v), k) for k, v in data.items()), "to", DATA)


if __name__ == "__main__":
    main()
