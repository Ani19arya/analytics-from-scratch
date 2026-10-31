"""Lesson 11: attribution models. Worked answer.

For each purchase, the path is the user's touches at or before the purchase time and
no more than LOOKBACK_DAYS before it, oldest first (ties in time by channel name).
Each model hands out exactly 1 conversion of credit across the path:
  first       all of it to the first touch
  last        all of it to the last touch
  linear      1 / k to each of the k touches
  time_decay  a touch d days before the purchase gets weight 0.5 ** (d / half_life),
              and the weights are scaled to add up to 1
A purchase with an empty path gives its credit to NO_TOUCH.
"""
import csv
import datetime

LOOKBACK_DAYS = 30
NO_TOUCH = "(none)"
MODELS = ("first", "last", "linear", "time_decay")


def parse_time(text):
    """'2026-10-01 14:05' -> datetime."""
    return datetime.datetime.strptime(text, "%Y-%m-%d %H:%M")


def load(touch_path, conv_path, lookback_days=LOOKBACK_DAYS):
    """Return a list of purchases, oldest first (ties by user_id), each
    {"user_id", "time", "revenue", "path"} where path is a list of (time, channel)."""
    touches = {}
    with open(touch_path, newline="") as f:
        for row in csv.DictReader(f):
            touches.setdefault(row["user_id"], []).append((parse_time(row["touch_time"]), row["channel"]))
    window = datetime.timedelta(days=lookback_days)
    out = []
    with open(conv_path, newline="") as f:
        for row in csv.DictReader(f):
            t = parse_time(row["conversion_time"])
            path = sorted(p for p in touches.get(row["user_id"], []) if t - window <= p[0] <= t)
            out.append({"user_id": row["user_id"], "time": t, "revenue": float(row["revenue"]), "path": path})
    out.sort(key=lambda c: (c["time"], c["user_id"]))
    return out


def weights(path, model, conv_time, half_life_days=7.0):
    """{channel: share of this purchase}. The shares add up to 1."""
    if model not in MODELS:
        raise ValueError("unknown model: %s" % model)
    if not path:
        return {NO_TOUCH: 1.0}
    if model == "first":
        raw = [1.0] + [0.0] * (len(path) - 1)
    elif model == "last":
        raw = [0.0] * (len(path) - 1) + [1.0]
    elif model == "linear":
        raw = [1.0] * len(path)
    else:
        raw = [0.5 ** ((conv_time - t).total_seconds() / 86400.0 / half_life_days) for t, _ in path]
    total = sum(raw)
    out = {}
    for (_, channel), w in zip(path, raw):
        if w:
            out[channel] = out.get(channel, 0.0) + w / total
    return out


def attribute(purchases, model, value="count", half_life_days=7.0):
    """{channel: credited purchases} (value="count") or {channel: credited revenue}
    (value="revenue"). The credits add up to the number of purchases or the total revenue."""
    out = {}
    for p in purchases:
        amount = 1.0 if value == "count" else p["revenue"]
        for channel, w in weights(p["path"], model, p["time"], half_life_days).items():
            out[channel] = out.get(channel, 0.0) + amount * w
    return out


def spread(purchases, models=MODELS):
    """{channel: (lowest credit, highest credit)} across the models, in purchases."""
    tables = [attribute(purchases, m) for m in models]
    channels = set()
    for t in tables:
        channels |= set(t)
    return {c: (min(t.get(c, 0.0) for t in tables), max(t.get(c, 0.0) for t in tables)) for c in channels}


if __name__ == "__main__":
    import os
    data = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    purchases = load(os.path.join(data, "touchpoints.csv"), os.path.join(data, "conversions.csv"))
    tables = {m: attribute(purchases, m) for m in MODELS}
    channels = sorted(set().union(*tables.values()))
    print("%-12s" % "channel" + "".join("%12s" % m for m in MODELS))
    for c in channels:
        print("%-12s" % c + "".join("%12.1f" % tables[m].get(c, 0.0) for m in MODELS))
    print("%-12s" % "total" + "".join("%12.1f" % sum(tables[m].values()) for m in MODELS))
    rev = attribute(purchases, "linear", value="revenue")
    print("linear revenue: " + ", ".join("%s %.2f" % (c, rev[c]) for c in sorted(rev)),
          "| total %.2f" % sum(p["revenue"] for p in purchases))
