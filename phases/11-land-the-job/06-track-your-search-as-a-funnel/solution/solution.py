"""Solution: a job search funnel with right-censoring, Wilson intervals by channel, and a
recommendation that only moves time when the evidence is clear."""
import csv
import datetime
import math
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
AS_OF = "2026-10-31"
Z95 = 1.96
STAGES = [("applied_on", "reply_on"), ("reply_on", "interview_on"), ("interview_on", "offer_on")]


def load_applications():
    with open(os.path.join(DATA, "applications.csv"), newline="") as f:
        return list(csv.DictReader(f))


def days_between(a, b):
    return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days


def wilson(k, n, z=Z95):
    """95% Wilson score interval for k successes out of n. (0.0, 1.0) when n is 0."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def stage_counts(apps, from_col, to_col, as_of=AS_OF, wait_days=21):
    """Count one step of the funnel among rows that reached from_col.

    passed:  to_col has a date
    failed:  no to_col, and either a rejection is recorded or wait_days have gone by since from_col
    waiting: no to_col, no rejection, younger than wait_days (right-censored: left out of n)
    Return {"k": passed, "n": passed + failed, "waiting": waiting}.
    """
    k = failed = waiting = 0
    for a in apps:
        if not a.get(from_col):
            continue
        if a.get(to_col):
            k += 1
        elif a.get("rejected_on") or days_between(a[from_col], as_of) >= wait_days:
            failed += 1
        else:
            waiting += 1
    return {"k": k, "n": k + failed, "waiting": waiting}


def funnel(apps, as_of=AS_OF, wait_days=21):
    """[(from_col, to_col, counts)] for the three steps: applied to reply, reply to interview,
    interview to offer."""
    return [(f, t, stage_counts(apps, f, t, as_of, wait_days)) for f, t in STAGES]


def replied_within(apps, days, as_of=AS_OF):
    """(k, n): among applications at least `days` old, how many had a reply within `days`."""
    old = [a for a in apps if days_between(a["applied_on"], as_of) >= days]
    k = sum(1 for a in old if a["reply_on"] and days_between(a["applied_on"], a["reply_on"]) <= days)
    return k, len(old)


def by_channel(apps, as_of=AS_OF, wait_days=28):
    """Per channel: applications to interviews with censoring, a Wilson interval, mean hours
    per application, and interviews per 10 hours (with the interval scaled the same way).

    Return {channel: {"k", "n", "waiting"} from stage_counts(applied_on -> interview_on), plus
    "apps": applications in the channel, "rate": k / n (None when n is 0), "low" and "high":
    the Wilson interval, "hours": mean hours_spent over ALL the channel's applications,
    "per_10h": rate x 10 / hours (None when n is 0), "low_10h" and "high_10h": low and high
    scaled the same way}.
    """
    out = {}
    for ch in sorted({a["channel"] for a in apps}):
        rows = [a for a in apps if a["channel"] == ch]
        c = stage_counts(rows, "applied_on", "interview_on", as_of, wait_days)
        low, high = wilson(c["k"], c["n"])
        hours = sum(float(a["hours_spent"]) for a in rows) / len(rows)
        rate = c["k"] / c["n"] if c["n"] else None
        out[ch] = dict(c, apps=len(rows), rate=rate, low=low, high=high, hours=hours,
                       per_10h=None if rate is None else rate * 10 / hours,
                       low_10h=low * 10 / hours, high_10h=high * 10 / hours)
    return out


def recommend(stats):
    """Best channel by interviews per 10 hours, and whether the evidence is clear: its lower
    bound is above every other channel's upper bound. None if no channel has a decided row."""
    known = {ch: s for ch, s in stats.items() if s["n"] > 0}
    if not known:
        return None
    best = sorted(known, key=lambda ch: (-known[ch]["per_10h"], ch))[0]
    clear = all(known[best]["low_10h"] > s["high_10h"] for ch, s in known.items() if ch != best)
    return {"best": best, "confident": clear}


if __name__ == "__main__":
    A = load_applications()
    for f, t, c in funnel(A):
        print(f, "->", t, c)
    stats = by_channel(A)
    for ch, s in stats.items():
        print(ch, s["k"], s["n"], s["waiting"], round(s["per_10h"], 2))
    print(recommend(stats))
