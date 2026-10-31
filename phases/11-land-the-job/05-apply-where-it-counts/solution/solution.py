"""Solution: score saved postings on freshness, fit and red flags, then choose which to apply
to inside a weekly time budget with an exact 0/1 knapsack."""
import csv
import datetime
import json
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")

STALE_DAYS = 30          # freshness falls from 1 to 0 over this many days
MUST_WEIGHT = 0.75       # fit = 0.75 x must-have share + 0.25 x nice-to-have share
REPOST_FACTOR = 0.5      # a reposted listing is worth half: its date is not the employer's
HARD_FLAGS = {"fee_to_apply", "unpaid_work", "seniority_mismatch"}

FEE = re.compile(r"\b(application|processing|registration) fee\b|\bpay to apply\b", re.I)
UNPAID = re.compile(r"\bunpaid (trial|test|pilot)\b|\bfree trial work\b", re.I)
NEGATION = re.compile(r"\b(no|never|not)\b", re.I)
SENIOR_WORDS = re.compile(r"\b(senior|sr|lead|principal|staff|manager|head|director)\b", re.I)


def load_postings():
    with open(os.path.join(DATA, "postings.csv"), newline="") as f:
        return list(csv.DictReader(f))


def load_profile():
    with open(os.path.join(DATA, "profile.json")) as f:
        return json.load(f)


def freshness(first_seen, as_of):
    """1.0 for a posting first seen today, falling in a straight line to 0.0 at STALE_DAYS.
    Blank or unreadable dates count as stale (0.0). A date after as_of counts as today."""
    try:
        seen = datetime.date.fromisoformat(first_seen)
    except (TypeError, ValueError):
        return 0.0
    days = (datetime.date.fromisoformat(as_of) - seen).days
    return max(0.0, 1.0 - max(days, 0) / STALE_DAYS)


def split_skills(cell):
    return {s.strip().lower() for s in (cell or "").split(";") if s.strip()}


def fit(posting, skills):
    """Return (fit score 0..1, sorted list of missing must-haves, lower case).
    A posting with no must-haves has a must-have share of 1; no nice-to-haves, a share of 1."""
    have = {s.lower() for s in skills}
    must, nice = split_skills(posting["must_have"]), split_skills(posting["nice_to_have"])
    must_share = len(must & have) / len(must) if must else 1.0
    nice_share = len(nice & have) / len(nice) if nice else 1.0
    return MUST_WEIGHT * must_share + (1 - MUST_WEIGHT) * nice_share, sorted(must - have)


def _said(pattern, text):
    """True if a sentence of text matches pattern and does not negate it."""
    for sentence in re.split(r"[.!?]", text or ""):
        if pattern.search(sentence) and not NEGATION.search(sentence):
            return True
    return False


def red_flags(posting, profile):
    """Sorted list of flag codes: fee_to_apply, unpaid_work, seniority_mismatch, repost."""
    flags = []
    if _said(FEE, posting["notes"]):
        flags.append("fee_to_apply")
    if _said(UNPAID, posting["notes"]):
        flags.append("unpaid_work")
    if posting["seniority_label"].strip().lower() == "entry level":
        low = posting.get("salary_min_usd") or ""
        too_rich = low != "" and float(low) >= profile["entry_salary_ceiling_usd"]
        if SENIOR_WORDS.search(posting["title"]) or too_rich:
            flags.append("seniority_mismatch")
    if posting["source"] == "repost":
        flags.append("repost")
    return sorted(flags)


def value(posting, profile):
    """Points for applying: 0 with a hard flag or more than one missing must-have, else
    100 x fit x (0.5 + 0.5 x freshness), halved for a repost."""
    flags = red_flags(posting, profile)
    score, missing = fit(posting, profile["skills"])
    if HARD_FLAGS & set(flags) or len(missing) > 1:
        return 0.0
    v = 100.0 * score * (0.5 + 0.5 * freshness(posting["first_seen"], profile["as_of"]))
    return v * REPOST_FACTOR if "repost" in flags else v


def choose(items, budget_hours):
    """Exact 0/1 knapsack. items: [(id, value, hours)], hours in steps of 0.5.
    Return (sorted chosen ids, total value, total hours) with the most value inside the budget.
    Items with value 0 or less are never chosen."""
    cap = int(round(budget_hours * 2))
    items = [(i, v, int(round(h * 2))) for i, v, h in items if v > 0]
    best = [0.0] * (cap + 1)
    took = []
    for _, v, w in items:
        row = [False] * (cap + 1)
        for c in range(cap, w - 1, -1):
            if best[c - w] + v > best[c] + 1e-9:
                best[c] = best[c - w] + v
                row[c] = True
        took.append(row)
    chosen, c = [], cap
    for k in range(len(items) - 1, -1, -1):
        if took[k][c]:
            chosen.append(items[k][0])
            c -= items[k][2]
    hours = sum(w for i, _, w in items if i in chosen) / 2
    return sorted(chosen), sum(v for i, v, _ in items if i in chosen), hours


def greedy(items, budget_hours):
    """The common shortcut: take the best value per hour first while it fits. Not always optimal."""
    left, chosen = budget_hours, []
    for i, v, h in sorted(items, key=lambda x: (-x[1] / x[2], x[0])):
        if v > 0 and h <= left:
            chosen.append((i, v, h))
            left -= h
    return sorted(i for i, _, _ in chosen), sum(v for _, v, _ in chosen), budget_hours - left


def plan(postings, profile):
    items = [(p["posting_id"], value(p, profile), float(p["est_hours"])) for p in postings]
    return choose(items, profile["weekly_hours"])


if __name__ == "__main__":
    P, prof = load_postings(), load_profile()
    ids, total, hours = plan(P, prof)
    print(ids, round(total, 1), hours)
