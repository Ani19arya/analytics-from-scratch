"""Capstone 11-08: a 30-day job search plan. The worked solution.

Read this after you have built your own in exercise.py. Run it from the
lesson folder to write solution/plan.json and print a summary:

    python3 solution/solution.py

Standard library only. The data is synthetic (see make_data.py).
"""
import csv
import datetime
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LESSON = os.path.dirname(HERE)

# ---- given (the same in exercise.py) ---------------------------------------

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


# ---- the functions the checker calls ---------------------------------------

def sponsorship_stated(text):
    """'no' if the text has any SPONSOR_NO phrase, else 'yes' if any SPONSOR_YES phrase, else 'not_stated'.
    Case does not matter."""
    t = (text or "").lower()
    if any(p in t for p in SPONSOR_NO):
        return "no"
    if any(p in t for p in SPONSOR_YES):
        return "yes"
    return "not_stated"


def red_flags(text):
    """The RED_FLAGS phrases found in the text (case does not matter), in RED_FLAGS order."""
    t = (text or "").lower()
    return [p for p in RED_FLAGS if p in t]


def is_eligible(posting, profile):
    """Can this person be hired for this posting, on the posting's own words? (DELIVERABLES.md, rule 1)
    Remote: only if remote_regions names one of profile["home_regions"]. On site or hybrid in the home
    country: only in profile["onsite_cities"]. On site or hybrid elsewhere: only if the text says yes to
    sponsorship."""
    if posting["work_mode"] == "remote":
        regions = {r.strip() for r in posting["remote_regions"].split(";") if r.strip()}
        return bool(regions & set(profile["home_regions"]))
    if posting["country"] == profile["home_country"]:
        return posting["city"] in profile["onsite_cities"]
    return sponsorship_stated(posting["description"]) == "yes"


def is_stale(posting, profile):
    """Posted more than stale_after_days before the plan starts, or closed before it starts."""
    start = profile["plan_start"]
    if days_between(posting["posted_date"], start) > profile["stale_after_days"]:
        return True
    return bool(posting["closes_on"]) and posting["closes_on"] < start


def title_family(title):
    """The first family in FAMILY_ORDER with a synonym inside the title (lowercased), or None."""
    t = (title or "").lower()
    for fam in FAMILY_ORDER:
        if any(s in t for s in TITLE_FAMILIES[fam]):
            return fam
    return None


def role_key(posting):
    """Company, title and city, lowercased and trimmed: two postings with the same key are one role."""
    return tuple(posting[k].strip().lower() for k in ("company", "title", "city"))


def usable_postings(postings, log, profile):
    """Postings worth a planned application: eligible, not stale, no red flag, in a target family,
    and a role not already in the log. One per role (the newest posted_date, then the smallest id),
    sorted by posting_id."""
    by_id = {p["posting_id"]: p for p in postings}
    done = {role_key(by_id[r["posting_id"]]) for r in log if r["posting_id"] in by_id}
    best = {}
    for p in postings:
        if not is_eligible(p, profile) or is_stale(p, profile) or red_flags(p["description"]):
            continue
        if title_family(p["title"]) not in profile["target_families"]:
            continue
        k = role_key(p)
        if k in done:
            continue
        if k not in best or (p["posted_date"], -int(p["posting_id"][1:])) > \
                (best[k]["posted_date"], -int(best[k]["posting_id"][1:])):
            best[k] = p
    return sorted(best.values(), key=lambda p: p["posting_id"])


def funnel(log):
    """Funnel metrics from an application log (see DELIVERABLES.md for every definition)."""
    apps = {}
    for r in log:
        a = apps.setdefault(r["application_id"], {"channel": r["channel"] or "unknown", "stage": 0,
                                                  "responded": False, "rejected": False})
        ev = r["event"]
        if ev != "applied":
            a["responded"] = True
        if ev == "rejected":
            a["rejected"] = True
        a["stage"] = max(a["stage"], STAGE_RANK.get(ev, 0))
    n = len(apps)
    responses = sum(1 for a in apps.values() if a["responded"])
    screens = sum(1 for a in apps.values() if a["stage"] >= 1)
    interviews = sum(1 for a in apps.values() if a["stage"] >= 2)
    by_channel = {}
    for a in apps.values():
        c = by_channel.setdefault(a["channel"], {"applications": 0, "screens": 0})
        c["applications"] += 1
        c["screens"] += 1 if a["stage"] >= 1 else 0
    for c in by_channel.values():
        c["screen_rate"] = c["screens"] / c["applications"]
    return {"applications": n, "responses": responses, "screens": screens, "interviews": interviews,
            "offers": sum(1 for a in apps.values() if a["stage"] >= 3),
            "rejections": sum(1 for a in apps.values() if a["rejected"]),
            "no_reply": n - responses,
            "response_rate": responses / n if n else None,
            "screen_rate": screens / n if n else None,
            "interview_rate": interviews / screens if screens else None,
            "by_channel": by_channel}


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
    out = {}
    for t in plan["tasks"]:
        out[t["week"]] = out.get(t["week"], 0.0) + t["hours"]
    return out


def match_share(posting, profile):
    tools = [t for t in posting["tools"].split(";") if t]
    return sum(1 for t in tools if t in profile["skills"]) / len(tools) if tools else 0.0


def build_plan(postings, log, profile):
    """The 30-day plan as a dict: {"seeker", "start", "end", "hours_per_week", "search_terms", "tasks"}.
    Each task: {"date", "week", "kind", "hours", "note"}, plus "posting_id" for kind "apply" and
    "funnel" for kind "review". The structure and the rules are in DELIVERABLES.md."""
    start = profile["plan_start"]
    end = add_days(start, profile["plan_days"] - 1)
    pool = usable_postings(postings, log, profile)
    # her level first (two years' experience: Senior titles go last), then the best skill match,
    # then the one closing soonest, then the newest
    pool.sort(key=lambda p: ("senior" in p["title"].lower(), -match_share(p, profile), p["closes_on"] or "9999-12-31",
                             -days_between("2000-01-01", p["posted_date"]), p["posting_id"]))
    tasks = []

    def add(date, kind, note, **extra):
        t = {"date": date, "week": week_of(date, start), "kind": kind, "hours": TASK_HOURS[kind], "note": note}
        t.update(extra)
        tasks.append(t)

    def apply_on(date):
        for i, p in enumerate(pool):
            if not p["closes_on"] or p["closes_on"] >= date:
                pool.pop(i)
                add(date, "apply", "%s, %s (%s)" % (p["title"], p["company"], p["city"]), posting_id=p["posting_id"])
                return

    baseline = funnel(log)
    full_weeks = profile["plan_days"] // 7
    for w in range(full_weeks):
        monday = add_days(start, 7 * w)
        add(monday, "review", "Weekly review: last week's funnel, then adjust this week",
            funnel=baseline if w == 0 else None)
        add(monday, "search", "Refresh saved searches with every term; save new postings")
        add(add_days(monday, 1), "network", "Ask one contact for a referral at a target company")
        add(add_days(monday, 3), "network", "Ask one contact for a referral at a target company")
        for d in (1, 2, 3, 4, 5):
            apply_on(add_days(monday, d))
    last = add_days(start, 7 * full_weeks)
    if last <= end:
        add(last, "review", "Final review: the 30-day funnel against the baseline", funnel=None)
        add(last, "follow_up", "Follow up on applications with no reply after 14 days")
        if add_days(last, 1) <= end:
            apply_on(add_days(last, 1))
    tasks.sort(key=lambda t: (t["date"], list(TASK_HOURS).index(t["kind"])))
    terms = [s for fam in FAMILY_ORDER if fam in profile["target_families"] for s in TITLE_FAMILIES[fam]]
    return {"seeker": profile["name"], "start": start, "end": end, "hours_per_week": profile["hours_per_week"],
            "search_terms": terms, "tasks": tasks}


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
    probs = set()
    start = profile["plan_start"]
    end = add_days(start, profile["plan_days"] - 1)
    if plan.get("start") != start or plan.get("end") != end:
        probs.add("window")
    tasks = plan.get("tasks", [])
    for t in tasks:
        if not (start <= t["date"] <= end):
            probs.add("window")
        if t["week"] != week_of(t["date"], start):
            probs.add("week")
        if t["kind"] not in TASK_HOURS or t["hours"] < TASK_HOURS[t["kind"]]:
            probs.add("task_hours")
    budgets = week_budgets(profile)
    for w, h in weekly_hours(plan).items():
        if w in budgets and h > budgets[w] + 1e-9:  # a week outside the plan is a "window" problem
            probs.add("hours")
    by_id = {p["posting_id"]: p for p in postings}
    done = {role_key(by_id[r["posting_id"]]) for r in log if r["posting_id"] in by_id}
    seen = set()
    applies = [t for t in tasks if t["kind"] == "apply"]
    for t in applies:
        p = by_id.get(t.get("posting_id"))
        if p is None or not is_eligible(p, profile):
            probs.add("ineligible")
            continue
        if is_stale(p, profile) or (p["closes_on"] and t["date"] > p["closes_on"]):
            probs.add("stale")
        if red_flags(p["description"]):
            probs.add("red_flag")
        if title_family(p["title"]) not in profile["target_families"]:
            probs.add("not_target")
        k = role_key(p)
        if k in seen or k in done:
            probs.add("duplicate")
        seen.add(k)
    usable = usable_postings(postings, log, profile)
    if len(applies) < min(MIN_APPLICATIONS, len(usable)):
        probs.add("volume")
    terms = [s.lower() for s in plan.get("search_terms", [])]
    allowed = {s: f for f in profile["target_families"] for s in TITLE_FAMILIES[f]}
    if any(s not in allowed for s in terms):
        probs.add("coverage")
    for f in profile["target_families"]:
        if sum(1 for s in set(terms) if allowed.get(s) == f) < 2:
            probs.add("coverage")
    for p in usable:
        if not any(s in p["title"].lower() for s in terms):
            probs.add("coverage")
    reviews = sorted((t for t in tasks if t["kind"] == "review"), key=lambda t: t["date"])
    for w in range(1, profile["plan_days"] // 7 + 1):
        if not any(t["week"] == w for t in reviews):
            probs.add("review")
    if not reviews or not same_funnel(reviews[0].get("funnel"), funnel(log)):
        probs.add("funnel")
    return sorted(probs)


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
