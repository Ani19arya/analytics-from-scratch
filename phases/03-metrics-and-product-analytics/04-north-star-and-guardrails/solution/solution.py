"""Lesson 04: north star and guardrails. Worked answer.

North star: share of job seekers who send at least one application (applying users).
Guardrail 1: employer reply rate = replies / applications (quality for employers).
Guardrail 2: unsubscribe rate = unsubscribed users / users (harm to job seekers).
"""
import csv


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
    """Return {"north_star", "reply_rate", "unsubscribe_rate"} for one variant summary."""
    return {
        "north_star": s["applying_users"] / s["users"] if s["users"] else 0.0,
        "reply_rate": s["replies"] / s["applications"] if s["applications"] else 0.0,
        "unsubscribe_rate": s["unsubscribes"] / s["users"] if s["users"] else 0.0,
    }


def decide(control, treatment, min_lift=0.02, max_reply_drop=0.02, max_unsub_rise=0.005):
    """The launch rule, written before the test:
    launch only if the north star rises by at least min_lift (absolute)
    AND reply_rate falls by no more than max_reply_drop
    AND unsubscribe_rate rises by no more than max_unsub_rise.
    Return {"decision": "launch" or "do not launch", "north_star_lift": float,
            "breaches": sorted list of guardrail names that failed}."""
    lift = treatment["north_star"] - control["north_star"]
    breaches = []
    if control["reply_rate"] - treatment["reply_rate"] > max_reply_drop:
        breaches.append("reply_rate")
    if treatment["unsubscribe_rate"] - control["unsubscribe_rate"] > max_unsub_rise:
        breaches.append("unsubscribe_rate")
    ok = lift >= min_lift and not breaches
    return {"decision": "launch" if ok else "do not launch", "north_star_lift": lift, "breaches": sorted(breaches)}


if __name__ == "__main__":
    import os
    data = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "experiment.csv")
    summary = summarize(data)
    for v in ("control", "quick_apply"):
        print(v, summary[v], {k: round(x, 4) for k, x in metrics(summary[v]).items()})
    print(decide(metrics(summary["control"]), metrics(summary["quick_apply"])))
