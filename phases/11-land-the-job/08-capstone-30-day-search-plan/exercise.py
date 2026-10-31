"""Capstone 11-08: a 30-day job search plan. Your submission.

Read BRIEF.md (Kavya's situation) and DELIVERABLES.md (what to hand in and
every definition the checker uses). Fill in every function marked TODO, then:

    python3 test_lesson.py      checks your functions and your plan
    python3 exercise.py         writes your plan to plan.json and prints a summary

Standard library only. The data is synthetic (see make_data.py).
"""
import csv
import datetime
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LESSON = HERE

# ---- given -----------------------------------------------------------------

TITLE_FAMILIES = {
    "bi": ["business intelligence", "bi analyst", "bi developer"],
    "product": ["product analyst", "growth analyst"],
    "business": ["business analyst", "operations analyst"],
    "data": ["data analyst", "insights analyst", "reporting analyst", "analytics analyst"],
}
FAMILY_ORDER = ["bi", "product", "business", "data"]
SPONSOR_YES = ["visa sponsorship available", "we sponsor visas"]
SPONSOR_NO = ["no visa sponsorship", "unable to sponsor", "must have the right to work"]
RED_FLAGS = ["registration fee", "pay for your training", "guaranteed job", "whatsapp only", "security deposit"]
TASK_HOURS = {"apply": 1.5, "network": 0.5, "search": 0.5, "follow_up": 0.25, "review": 1.0, "skill": 1.0}
STAGE_RANK = {"applied": 0, "screen": 1, "phone_screen": 1, "interview": 2, "offer": 3}
MIN_APPLICATIONS = 16


def load(folder):
    """Read data/postings.csv, data/app_log.csv and data/profile.json from `folder`."""
    out = {}
    for name in ("postings", "app_log"):
        with open(os.path.join(folder, name + ".csv"), newline="") as f:
            out[name] = list(csv.DictReader(f))
    with open(os.path.join(folder, "profile.json")) as f:
        out["profile"] = json.load(f)
    return out


def add_days(date_text, n):
    """'2026-11-02', 3 -> '2026-11-05'."""
    return (datetime.date.fromisoformat(date_text) + datetime.timedelta(days=n)).isoformat()


def days_between(a, b):
    """Days from date a to date b (b - a), both 'YYYY-MM-DD'."""
    return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days


# ---- yours: the functions the checker calls --------------------------------

def sponsorship_stated(text):
    """'no' if the text has any SPONSOR_NO phrase, else 'yes' if any SPONSOR_YES phrase, else 'not_stated'.
    Case does not matter."""
    # TODO
    raise NotImplementedError


def red_flags(text):
    """The RED_FLAGS phrases found in the text (case does not matter), in RED_FLAGS order."""
    # TODO
    raise NotImplementedError


def is_eligible(posting, profile):
    """Can this person be hired for this posting, on the posting's own words? (DELIVERABLES.md, rule 1)
    Remote: only if remote_regions names one of profile["home_regions"]. On site or hybrid in the home
    country: only in profile["onsite_cities"]. On site or hybrid elsewhere: only if the text says yes to
    sponsorship."""
    # TODO
    raise NotImplementedError


def is_stale(posting, profile):
    """Posted more than stale_after_days before the plan starts, or closed before it starts."""
    # TODO
    raise NotImplementedError


def title_family(title):
    """The first family in FAMILY_ORDER with a synonym inside the title (lowercased), or None."""
    # TODO
    raise NotImplementedError


def role_key(posting):
    """Company, title and city, lowercased and trimmed: two postings with the same key are one role."""
    # TODO
    raise NotImplementedError


def usable_postings(postings, log, profile):
    """Postings worth a planned application: eligible, not stale, no red flag, in a target family,
    and a role not already in the log. One per role (the newest posted_date, then the smallest id),
    sorted by posting_id."""
    # TODO
    raise NotImplementedError


def funnel(log):
    """Funnel metrics from an application log (see DELIVERABLES.md for every definition)."""
    # TODO
    raise NotImplementedError


def week_of(date_text, start):
    """Plan week of a date: days 1-7 are week 1."""
    return days_between(start, date_text) // 7 + 1


def week_budgets(profile):
    """{week: hours}. A week has hours_per_week; the short last week gets its share by days."""
    out = {}
    for d in range(profile["plan_days"]):
        w = d // 7 + 1
        out[w] = out.get(w, 0.0) + profile["hours_per_week"] / 7.0
    return out


def weekly_hours(plan):
    """{week: total planned hours}, from the tasks' own week field."""
    # TODO
    raise NotImplementedError


def build_plan(postings, log, profile):
    """The 30-day plan as a dict: {"seeker", "start", "end", "hours_per_week", "search_terms", "tasks"}.
    Each task: {"date", "week", "kind", "hours", "note"}, plus "posting_id" for kind "apply" and
    "funnel" for kind "review". The structure and the rules are in DELIVERABLES.md."""
    # TODO
    raise NotImplementedError


def same_funnel(a, b):
    """True when funnel dict a matches funnel dict b: same counts, rates within 1e-9, same channels."""
    if a is None or b is None:
        return a is b
    for k, v in b.items():
        if k == "by_channel":
            if set(a.get(k, {})) != set(v):
                return False
            if not all(same_funnel(a[k][c], v[c]) for c in v):
                return False
        elif isinstance(v, float) or isinstance(a.get(k), float):
            if a.get(k) is None or abs(a[k] - v) > 1e-9:
                return False
        elif a.get(k) != v:
            return False
    return True


def plan_problems(plan, postings, log, profile):
    """Every rule the plan breaks, as a sorted list of distinct codes (see DELIVERABLES.md). [] = valid."""
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    d = load(os.path.join(LESSON, "data"))
    plan = build_plan(d["postings"], d["app_log"], d["profile"])
    with open(os.path.join(HERE, "plan.json"), "w") as f:
        json.dump(plan, f, indent=2, sort_keys=True)
        f.write("\n")
    usable = usable_postings(d["postings"], d["app_log"], d["profile"])
    print("usable postings:", len(usable))
    print("applications planned:", sum(1 for t in plan["tasks"] if t["kind"] == "apply"))
    print("hours by week:", {w: round(h, 2) for w, h in sorted(weekly_hours(plan).items())})
    print("problems:", plan_problems(plan, d["postings"], d["app_log"], d["profile"]))
