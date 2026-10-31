"""Build data/orders.csv and data/results.csv for a fictional food delivery app, Tiffinbell.

The story: for four weeks, every Pune order was sent at random to the current dispatch rule
or to a new one. orders.csv is one row per order. results.csv is the analysis a teammate ran
on it: on-time rates, the change in points, a 95% interval, and the decision it supports.
The executive summary in this lesson may only quote numbers that are in results.csv.

orders.csv columns: order_id, order_date, rule (current or new), promised_min, actual_min.
An order is on time when actual_min <= promised_min.
results.csv columns: name, value. Every value is text, already rounded the way it should be quoted.

The data is synthetic and deterministic (fixed seed). Tiffinbell and its orders are invented.
Each seed draws its own true effect of the new rule, so another seed can give a smaller,
a negative or an unclear result.
Run from the lesson folder: python3 make_data.py
In code: build(seed) returns {"orders": rows, "results": {name: value}} without writing files.
"""
import csv
import datetime
import math
import os
import random

SEED = 694
HERE = os.path.dirname(os.path.abspath(__file__))
START = datetime.date(2026, 10, 5)
DAYS = 28
BASE_ON_TIME = 0.80
ORDERS_HEADER = ["order_id", "order_date", "rule", "promised_min", "actual_min"]

FIXED = {
    "metric": "on-time delivery rate",
    "city": "Pune",
    "period": "5 October to 1 November 2026",
    "weeks": "4",
    "interval": "95% interval",
    "decision": "whether all four cities switch to the new rule",
    "decide_by": "13 November",
    "caveat": "this is Pune in ordinary weeks; the other cities and the festival peak may differ",
}
RECOMMEND = {
    "better": "switch all four cities",
    "worse": "keep the current rule",
    "unclear": "run the Pune test 4 more weeks",
}


def one_decimal(x):
    """x to one decimal place as text, with no "-0.0"."""
    text = "%.1f" % x
    return "0.0" if text == "-0.0" else text


def build_orders(seed):
    """One row per order: [order_id, order_date, rule, promised_min, actual_min]."""
    rng = random.Random(seed)
    effect = rng.uniform(-0.03, 0.05)  # this seed's true change in the on-time rate
    n = rng.randint(1700, 1900)
    rows = []
    for oid in range(1, n + 1):
        day = START + datetime.timedelta(days=rng.randrange(DAYS))
        rule = "new" if rng.random() < 0.5 else "current"
        promised = rng.choice([30, 35, 40, 45])
        p = BASE_ON_TIME + (effect if rule == "new" else 0.0)
        if rng.random() < p:
            actual = promised - rng.randint(0, 12)
        else:
            actual = promised + rng.randint(1, 25)
        rows.append([oid, day.isoformat(), rule, promised, actual])
    return rows


def analyse(orders):
    """The teammate's analysis: on-time rate by rule, the change in points and a 95% interval.
    Returns {name: value as text}, rounded the way the numbers should be quoted."""
    n = {"current": 0, "new": 0}
    on_time = {"current": 0, "new": 0}
    for _, _, rule, promised, actual in orders:
        n[rule] += 1
        on_time[rule] += int(int(actual) <= int(promised))
    p1, p2 = on_time["new"] / n["new"], on_time["current"] / n["current"]
    diff = p1 - p2
    se = math.sqrt(p1 * (1 - p1) / n["new"] + p2 * (1 - p2) / n["current"])
    low, high = one_decimal(100 * (diff - 1.96 * se)), one_decimal(100 * (diff + 1.96 * se))
    # the verdict reads the interval as it is quoted, so the words and the numbers agree
    if float(low) > 0:
        verdict = "better"
    elif float(high) < 0:
        verdict = "worse"
    else:
        verdict = "unclear"
    out = dict(FIXED)
    out.update({
        "control_orders": str(n["current"]),
        "control_on_time": str(on_time["current"]),
        "control_rate_pct": one_decimal(100 * p2),
        "pilot_orders": str(n["new"]),
        "pilot_on_time": str(on_time["new"]),
        "pilot_rate_pct": one_decimal(100 * p1),
        "change_pts": one_decimal(100 * diff),
        "ci_low_pts": low,
        "ci_high_pts": high,
        "verdict": verdict,
        "recommendation": RECOMMEND[verdict],
    })
    return out


def build(seed=SEED):
    orders = build_orders(seed)
    return {"orders": orders, "results": analyse(orders)}


def main():
    data = build()
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(os.path.join(HERE, "data", "orders.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(ORDERS_HEADER)
        w.writerows(data["orders"])
    with open(os.path.join(HERE, "data", "results.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "value"])
        for name, value in data["results"].items():
            w.writerow([name, value])
    print("wrote %d orders and %d results" % (len(data["orders"]), len(data["results"])))


if __name__ == "__main__":
    main()
