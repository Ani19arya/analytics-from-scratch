"""Lesson 07-08: the metrics case interview. Worked answer.

sign-ups = visits x start rate x finish rate
    start rate  = signup_starts / visits
    finish rate = signups / signup_starts
The order of the case: check the data, split the change into the funnel steps,
find the segment where it happened, then name the step inside that segment.
"""
import csv
import math
import os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
SPLIT = "2026-10-19"
STEPS = ("visits", "start_rate", "finish_rate")
DIMENSIONS = ("platform", "channel")
GAP_THRESHOLD = 0.8

ANSWER = """Clarify: sign-ups means the "signup completed" event, week of 19 October against the week of 12 October, all platforms and channels; nothing was launched on purpose except the new app releases.
Check the data: events and accounts in the production database agree on every app version (0.97 to 0.99), so the drop is real and not a tracking bug.
Break it down: sign-ups fell from 1,666 to 1,343 (-19.4%); visits and the start rate barely moved, the finish rate explains almost all of it.
Segment: web lost 302 of the 323 sign-ups (93%); ios and android are almost flat, and the drop is spread across every channel, so it is not one campaign.
Cause: on web, the finish rate fell from 53.3% to 32.8% while the start rate held at 12.2% to 12.3%, so people start the sign-up form and do not complete it.
Next step: ask what changed in the web sign-up form on 19 October, and check form errors by browser before anyone touches marketing.
"""


def load(name, data_dir=DATA):
    with open(os.path.join(data_dir, name), newline="") as f:
        return list(csv.DictReader(f))


def weekly_funnel(rows, split=SPLIT, dimension=None, value=None):
    """{"prior": totals, "current": totals}, where totals has visits, starts and signups.
    Days before split are prior, the rest current. With dimension and value, keep only
    the rows where row[dimension] == value."""
    out = {"prior": {"visits": 0, "starts": 0, "signups": 0},
           "current": {"visits": 0, "starts": 0, "signups": 0}}
    for r in rows:
        if dimension is not None and r[dimension] != value:
            continue
        t = out["prior"] if r["date"] < split else out["current"]
        t["visits"] += int(r["visits"])
        t["starts"] += int(r["signup_starts"])
        t["signups"] += int(r["signups"])
    return out


def rates(t):
    """visits, start_rate and finish_rate for one week's totals. A rate over 0 is 0.0."""
    return {
        "visits": t["visits"],
        "start_rate": t["starts"] / t["visits"] if t["visits"] else 0.0,
        "finish_rate": t["signups"] / t["starts"] if t["starts"] else 0.0,
    }


def log_mean(a, b):
    if a == b:
        return float(a)
    return (a - b) / (math.log(a) - math.log(b))


def decompose(prior, current):
    """Split current["signups"] - prior["signups"] into the three steps (LMDI).
    effect = L(current signups, prior signups) * ln(current step / prior step).
    Returns {"total": change, "visits": ..., "start_rate": ..., "finish_rate": ...}; the three
    effects add up to total. If any count is 0 in either week, the logs are undefined:
    the three effects are None and only total is filled in."""
    total = current["signups"] - prior["signups"]
    out = {"total": total}
    counts = [t[k] for t in (prior, current) for k in ("visits", "starts", "signups")]
    if any(v <= 0 for v in counts):
        for s in STEPS:
            out[s] = None
        return out
    rp, rc = rates(prior), rates(current)
    weight = log_mean(current["signups"], prior["signups"])
    for s in STEPS:
        out[s] = weight * math.log(rc[s] / rp[s])
    return out


def tracking_gaps(funnel_rows, account_rows, split=SPLIT, threshold=GAP_THRESHOLD):
    """App versions whose "signup completed" events in the current week are below
    threshold x the accounts the database created from that version.
    Returns [(app_version, events / accounts rounded to 2 places)], lowest ratio first.
    A version with no accounts that week is skipped (there is nothing to compare)."""
    events, accounts = {}, {}
    for r in funnel_rows:
        if r["date"] >= split:
            events[r["app_version"]] = events.get(r["app_version"], 0) + int(r["signups"])
    for r in account_rows:
        if r["date"] >= split:
            accounts[r["app_version"]] = accounts.get(r["app_version"], 0) + int(r["accounts"])
    gaps = []
    for version, n in accounts.items():
        if n == 0:
            continue
        ratio = events.get(version, 0) / n
        if ratio < threshold:
            gaps.append((version, round(ratio, 2)))
    return sorted(gaps, key=lambda g: (g[1], g[0]))


def segment_changes(rows, dimension, split=SPLIT):
    """[(value, prior signups, current signups, change)] for every value of dimension,
    biggest drop first (most negative change); ties by value. A value seen in only one
    week counts 0 in the other."""
    sums = {}
    for r in rows:
        s = sums.setdefault(r[dimension], [0, 0])
        s[0 if r["date"] < split else 1] += int(r["signups"])
    out = [(v, p, c, c - p) for v, (p, c) in sums.items()]
    return sorted(out, key=lambda x: (x[3], x[0]))


def diagnose(funnel_rows, account_rows, split=SPLIT):
    """The case in one dict: cause, dimension, segment, step and share.
    1. Tracking first: if tracking_gaps finds a version, the cause is "tracking", the
       dimension "app_version", the segment the lowest version, the step None.
    2. Otherwise the segment is the single value of platform or channel with the biggest
       drop in sign-ups (ties: platform before channel, then by value).
    3. The step is the funnel step with the most negative effect inside that segment;
       "visits" means the cause is "traffic", a rate means "conversion".
    share = segment change / total change, rounded to 2 places (None for tracking)."""
    gaps = tracking_gaps(funnel_rows, account_rows, split)
    if gaps:
        return {"cause": "tracking", "dimension": "app_version", "segment": gaps[0][0], "step": None, "share": None}
    total = weekly_funnel(funnel_rows, split)
    total_change = total["current"]["signups"] - total["prior"]["signups"]
    best = None
    for rank, dim in enumerate(DIMENSIONS):
        for value, _, _, change in segment_changes(funnel_rows, dim, split):
            key = (change, rank, value)
            if best is None or key < best[0]:
                best = (key, dim, value)
    _, dim, value = best
    seg = weekly_funnel(funnel_rows, split, dim, value)
    effects = decompose(seg["prior"], seg["current"])
    step = None
    if effects["visits"] is not None:
        step = min(STEPS, key=lambda s: (effects[s], STEPS.index(s)))
    share = round(best[0][0] / total_change, 2) if total_change else None
    return {"cause": "traffic" if step == "visits" else "conversion", "dimension": dim,
            "segment": value, "step": step, "share": share}


def main():
    funnel, accounts = load("funnel_daily.csv"), load("accounts_daily.csv")
    total = weekly_funnel(funnel)
    print("sign-ups:", total["prior"]["signups"], "->", total["current"]["signups"])
    print("tracking gaps:", tracking_gaps(funnel, accounts))
    print({k: (round(v, 1) if v is not None else None) for k, v in decompose(total["prior"], total["current"]).items()})
    for dim in DIMENSIONS:
        print(dim, segment_changes(funnel, dim))
    print(diagnose(funnel, accounts))


if __name__ == "__main__":
    main()
