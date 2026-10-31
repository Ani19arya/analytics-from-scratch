"""Exercise 07-08: the metrics case interview.

load, weekly_funnel, rates and log_mean are done for you. Fill in decompose,
tracking_gaps, segment_changes and diagnose, then write ANSWER. Run: python3 test_lesson.py

sign-ups = visits x start rate x finish rate
    start rate  = signup_starts / visits
    finish rate = signups / signup_starts
The order of the case: check the data, split the change into the funnel steps,
find the segment where it happened, then name the step inside that segment.
"""
import csv
import math
import os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SPLIT = "2026-10-19"
STEPS = ("visits", "start_rate", "finish_rate")
DIMENSIONS = ("platform", "channel")
GAP_THRESHOLD = 0.8

# TODO: after your code runs, write what you would say, one line per step, each line
# starting with its label: "Clarify:", "Check the data:", "Break it down:", "Segment:",
# "Cause:", "Next step:". Use the numbers your code prints.
ANSWER = """"""


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
    # TODO: the total change, then the LMDI effect of each step in STEPS.
    raise NotImplementedError


def tracking_gaps(funnel_rows, account_rows, split=SPLIT, threshold=GAP_THRESHOLD):
    """App versions whose "signup completed" events in the current week are below
    threshold x the accounts the database created from that version.
    Returns [(app_version, events / accounts rounded to 2 places)], lowest ratio first.
    A version with no accounts that week is skipped (there is nothing to compare)."""
    # TODO: sum events (funnel signups) and accounts by app_version for the current week, then compare.
    raise NotImplementedError


def segment_changes(rows, dimension, split=SPLIT):
    """[(value, prior signups, current signups, change)] for every value of dimension,
    biggest drop first (most negative change); ties by value. A value seen in only one
    week counts 0 in the other."""
    # TODO: sum signups per value of dimension in each week, then sort.
    raise NotImplementedError


def diagnose(funnel_rows, account_rows, split=SPLIT):
    """The case in one dict: cause, dimension, segment, step and share.
    1. Tracking first: if tracking_gaps finds a version, the cause is "tracking", the
       dimension "app_version", the segment the lowest version, the step None.
    2. Otherwise the segment is the single value of platform or channel with the biggest
       drop in sign-ups (ties: platform before channel, then by value).
    3. The step is the funnel step with the most negative effect inside that segment;
       "visits" means the cause is "traffic", a rate means "conversion".
    share = segment change / total change, rounded to 2 places (None for tracking)."""
    # TODO: follow the three numbered steps in the docstring. Reuse your functions above.
    raise NotImplementedError


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
