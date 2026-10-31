"""Build data/spend.csv and data/acquisitions.csv for the Plinkwell CAC case.

The data is synthetic and deterministic (fixed seed). Plinkwell is a fictional
language learning app with a paid subscription. 39 weeks, Monday 5 January to
Sunday 4 October 2026: weeks 1 to 13 are Q1, 14 to 26 Q2, 27 to 39 Q3.

spend.csv: week_start, channel, spend. Paid channels only: search, social,
video. Spend is per channel and week, not per platform.

acquisitions.csv: week_start, channel, platform, signups, subscribers.
channel is search, social, video, organic or unattributed (the app could not
tell where the person came from). platform is ios, android or web.
subscribers are new paying customers (people who finished the free trial and
paid).

The story planted in the data:
- Social spend grows from about 4,000 to about 10,000 a week. Social has
  diminishing returns: subscribers grow with the square root of spend, so
  each extra 1,000 buys fewer subscribers than the last.
- From week 27 (6 July) an iOS tracking change means most iOS social
  subscribers arrive with no channel: they land in "unattributed".
- Search and video spend and returns stay flat. The trial-to-paid rate stays
  the same all year (no pricing effect).

    python3 make_data.py                         writes data/*.csv (seed 707)
    import make_data; make_data.build(seed=12)   returns the rows for another seed
"""
import csv
import datetime
import math
import os
import random

SEED = 707
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
START = datetime.date(2026, 1, 5)
WEEKS = 39
BREAK_WEEK = 27
SPEND_FIELDS = ["week_start", "channel", "spend"]
ACQ_FIELDS = ["week_start", "channel", "platform", "signups", "subscribers"]
PLATFORMS = (("ios", 0.45), ("android", 0.40), ("web", 0.15))
CHANNELS = ("search", "social", "video", "organic", "unattributed")
TRIAL_TO_PAID = 0.25


def split(rng, total, shares):
    """Split an integer total across shares; the last share takes the remainder."""
    out, left = [], total
    for _, s in shares[:-1]:
        k = min(left, max(0, int(round(total * s * rng.uniform(0.9, 1.1)))))
        out.append(k)
        left -= k
    out.append(left)
    return out


def build(seed=SEED):
    """Return {"spend": [...], "acquisitions": [...]}, rows as dicts of text values."""
    rng = random.Random(seed)
    spend_rows, acq_rows = [], []
    for w in range(1, WEEKS + 1):
        day = (START + datetime.timedelta(weeks=w - 1)).isoformat()
        spend = {
            "search": 6000 * rng.uniform(0.93, 1.07),
            "social": (4000 + 6000 * (w - 1) / (WEEKS - 1)) * rng.uniform(0.95, 1.05),
            "video": 3000 * rng.uniform(0.93, 1.07),
        }
        subs = {
            "search": spend["search"] / 40.0,
            "social": 1.8 * math.sqrt(spend["social"]),
            "video": spend["video"] / 60.0,
            "organic": 150.0,
        }
        by_cp = {}
        for ch, mean in subs.items():
            n = max(0, int(round(rng.gauss(mean, math.sqrt(mean)))))
            for (plat, _), k in zip(PLATFORMS, split(rng, n, PLATFORMS)):
                by_cp[(ch, plat)] = k
        # a small baseline of unattributed subscribers, taken from organic
        for plat, _ in PLATFORMS:
            move = sum(1 for _ in range(by_cp[("organic", plat)]) if rng.random() < 0.08)
            by_cp[("organic", plat)] -= move
            by_cp[("unattributed", plat)] = move
        if w >= BREAK_WEEK:
            lost = sum(1 for _ in range(by_cp[("social", "ios")]) if rng.random() < 0.8)
            by_cp[("social", "ios")] -= lost
            by_cp[("unattributed", "ios")] += lost
        for ch in ("search", "social", "video"):
            spend_rows.append({"week_start": day, "channel": ch, "spend": "%.2f" % spend[ch]})
        for ch in CHANNELS:
            for plat, _ in PLATFORMS:
                k = by_cp[(ch, plat)]
                signups = k + sum(1 for _ in range(int(round(k / TRIAL_TO_PAID)) - k) if rng.random() < 0.97)
                acq_rows.append({"week_start": day, "channel": ch, "platform": plat,
                                 "signups": str(signups), "subscribers": str(k)})
    return {"spend": spend_rows, "acquisitions": acq_rows}


def write_csv(rows, fields, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    data = build()
    write_csv(data["spend"], SPEND_FIELDS, os.path.join(DATA, "spend.csv"))
    write_csv(data["acquisitions"], ACQ_FIELDS, os.path.join(DATA, "acquisitions.csv"))
    print("wrote", len(data["spend"]), "spend rows and", len(data["acquisitions"]), "acquisition rows to", DATA)


if __name__ == "__main__":
    main()
