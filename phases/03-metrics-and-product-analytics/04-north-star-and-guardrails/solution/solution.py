"""Lesson 04: north star and guardrails. Worked answer.

North star: share of job seekers who send at least one application (applying users).
Guardrail 1: employer reply rate = replies / applications (quality for employers).
Guardrail 2: unsubscribe rate = unsubscribed users / users (harm to job seekers).
The launch rule is noise-aware: it uses a 95% interval for each change.
"""
import csv
import math


def summarize(path):
    """Return {variant: {"users", "applying_users", "applications", "replies", "unsubscribes"}}."""
    out = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            s = out.setdefault(row["variant"], {"users": 0, "applying_users": 0, "applications": 0,
                                                "replies": 0, "unsubscribes": 0})
            apps = int(row["applications"])
            s["users"] += 1
            s["applying_users"] += 1 if apps > 0 else 0
            s["applications"] += apps
            s["replies"] += int(row["replies"])
            s["unsubscribes"] += int(row["unsubscribed"])
    return out


def metrics(s):
    """Return the three rates for one variant summary, plus the two denominators
    (users, applications) that the launch rule needs to size the noise."""
    return {
        "north_star": s["applying_users"] / s["users"] if s["users"] else 0.0,
        "reply_rate": s["replies"] / s["applications"] if s["applications"] else 0.0,
        "unsubscribe_rate": s["unsubscribes"] / s["users"] if s["users"] else 0.0,
        "users": s["users"],
        "applications": s["applications"],
    }


def diff_interval(p0, n0, p1, n1, z=1.96):
    """The change p1 - p0 between two proportions and its interval:
    se = sqrt(p0 (1 - p0) / n0 + p1 (1 - p1) / n1), interval = change -/+ z x se.
    Return (change, low, high), or None if either n is 0."""
    if n0 == 0 or n1 == 0:
        return None
    change = p1 - p0
    se = math.sqrt(p0 * (1 - p0) / n0 + p1 * (1 - p1) / n1)
    return change, change - z * se, change + z * se


def decide(control, treatment, min_lift=0.02, max_reply_drop=0.02, max_unsub_rise=0.005, z=1.96):
    """The launch rule, written before the test. All changes are absolute (treatment - control).
    Launch only if
      the north star lift is at least min_lift AND its interval is above 0 (not noise),
      AND the reply rate interval's low end is no lower than -max_reply_drop,
      AND the unsubscribe rate interval's high end is no higher than +max_unsub_rise.
    A guardrail whose interval cannot be computed (a denominator of 0) fails.
    Return {"decision", "north_star_lift", "intervals": {metric: (change, low, high) or None},
            "breaches": sorted list of guardrail names that failed}."""
    iv = {
        "north_star": diff_interval(control["north_star"], control["users"],
                                    treatment["north_star"], treatment["users"], z),
        "reply_rate": diff_interval(control["reply_rate"], control["applications"],
                                    treatment["reply_rate"], treatment["applications"], z),
        "unsubscribe_rate": diff_interval(control["unsubscribe_rate"], control["users"],
                                          treatment["unsubscribe_rate"], treatment["users"], z),
    }
    lift = treatment["north_star"] - control["north_star"]
    north_star_ok = iv["north_star"] is not None and lift >= min_lift and iv["north_star"][1] > 0
    breaches = []
    if iv["reply_rate"] is None or iv["reply_rate"][1] < -max_reply_drop:
        breaches.append("reply_rate")
    if iv["unsubscribe_rate"] is None or iv["unsubscribe_rate"][2] > max_unsub_rise:
        breaches.append("unsubscribe_rate")
    ok = north_star_ok and not breaches
    return {"decision": "launch" if ok else "do not launch", "north_star_lift": lift,
            "intervals": iv, "breaches": sorted(breaches)}


if __name__ == "__main__":
    import os
    data = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "experiment.csv")
    summary = summarize(data)
    c, t = metrics(summary["control"]), metrics(summary["quick_apply"])
    for v, mm in (("control", c), ("quick_apply", t)):
        print(v, summary[v])
    result = decide(c, t)
    for name in ("north_star", "reply_rate", "unsubscribe_rate"):
        change, low, high = result["intervals"][name]
        print("%-17s control %6.2f%%  quick_apply %6.2f%%  change %+6.2f points  95%% interval %+6.2f to %+6.2f" % (
            name, 100 * c[name], 100 * t[name], 100 * change, 100 * low, 100 * high))
    print("decision:", result["decision"], " breaches:", result["breaches"])
