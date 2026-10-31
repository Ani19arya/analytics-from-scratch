#!/usr/bin/env python3
"""One learner profile for every tutor mode: placement, lessons, mock interviews.

    python3 tools/progress.py status                     # skill map and the next lesson
    python3 tools/progress.py check 01-02                # run that lesson's test on YOUR exercise, record it
    python3 tools/progress.py placement --from result.json   # record a placement result
    python3 tools/progress.py placement --answers a.json     # grade a.json with placement.py and record it
    python3 tools/progress.py placement                  # save an answers template to fill in, then use --answers
    python3 tools/progress.py track interview-prep       # set your goal without a placement
    python3 tools/progress.py interview --template       # print an empty mock interview scorecard
    python3 tools/progress.py interview --from card.json # record a mock interview scorecard
    python3 tools/progress.py note "Joins still feel slow"
    python3 tools/progress.py report [--json | --md]     # before and after, for you or a portfolio
    python3 tools/progress.py export [--level coarse|full] [--out FILE] [--yes] [--new-id]
                                                         # opt-in pseudonymous pilot summary
    python3 tools/progress.py aggregate DIR [--json]     # pilot owner: metrics from many exports

The profile lives in .learner/profile.json at the repo root. It is gitignored, so it
stays on your computer. It is created the first time you run a command. Every command
takes --profile PATH to use another file (the tests use a temp folder). This script
writes only that profile (and, for `placement` with no options, an answers template
next to it). `check` runs the lesson test with `python3 -B`, so it leaves no
__pycache__ behind, and it always checks your exercise, never the solution.

Nothing is collected or sent. `export` is opt-in: it prints exactly what it includes,
waits for --yes or a typed y, then writes a pseudonymous summary (no notes, names, paths
or free text) for you to share only if you want to. Pseudonymous, not anonymous: there
is no name or contact details, but a random id and your activity pattern could still
point to you in a small group. The default --level coarse leaves out dates, tries and
scores; --level full keeps them and is meant to be sent privately to the pilot
organiser. See docs/PILOT.md.

How lessons map to skill areas. Each live lesson in curriculum.json belongs to one
area, so the counts add up to the course total:

    phase 00-start-here                  -> the area of its first skill below, else "foundations"
                                            (00-04 and 00-05 are sql, 00-06 is python)
    phase 01-sql                         -> sql
    phase 02-statistics-and-experiments  -> statistics
    phase 03-metrics-and-product-analytics -> metrics
    phase 04-dashboards                  -> dashboards
    phase 05-python-for-analysts         -> python
    phase 06-ai-for-analysts             -> ai
    phase 07-getting-hired               -> interviews
    phase 08-modern-data-stack           -> data-stack
    phase 09-business-case-studies       -> cases
    phase 10-capstone-projects           -> capstones
    phase 11-land-the-job                -> job-search
    skills -> area: sql -> sql, statistics/experimentation -> statistics, metrics -> metrics,
                    bi/excel -> dashboards, python -> python, genai -> ai

The first six areas are the placement check's areas, so status and report show the
placement score next to the lessons passed. A lesson's other skills that map to an
area are listed as "also" in the JSON output; they do not change the counts.

Standard library only, offline, Python 3.9 or later.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PROFILE = os.path.join(ROOT, ".learner", "profile.json")
PLACEMENT = os.path.join(ROOT, "tools", "placement.py")
VERSION = 1

AREAS = ["foundations", "sql", "statistics", "metrics", "dashboards", "python", "ai",
         "interviews", "data-stack", "cases", "capstones", "job-search"]
AREA_NAMES = {
    "foundations": "Foundations", "sql": "SQL", "statistics": "Statistics", "metrics": "Metrics",
    "dashboards": "Dashboards", "python": "Python", "ai": "AI evaluation", "interviews": "Getting hired",
    "data-stack": "Data stack", "cases": "Case studies", "capstones": "Capstones", "job-search": "Job search",
}
PLACEMENT_AREAS = ["sql", "statistics", "metrics", "dashboards", "python", "ai"]
PHASE_AREA = {
    "00-start-here": None,
    "01-sql": "sql",
    "02-statistics-and-experiments": "statistics",
    "03-metrics-and-product-analytics": "metrics",
    "04-dashboards": "dashboards",
    "05-python-for-analysts": "python",
    "06-ai-for-analysts": "ai",
    "07-getting-hired": "interviews",
    "08-modern-data-stack": "data-stack",
    "09-business-case-studies": "cases",
    "10-capstone-projects": "capstones",
    "11-land-the-job": "job-search",
}
SKILL_AREA = {"sql": "sql", "statistics": "statistics", "experimentation": "statistics", "metrics": "metrics",
              "bi": "dashboards", "excel": "dashboards", "python": "python", "genai": "ai"}
LEVELS = ["beginner", "intermediate", "advanced", "land-the-job"]

# Mock interview rounds, as in skills/analytics-from-scratch/INTERVIEW_RUBRIC.md.
ROUNDS = ["sql", "statistics", "metrics-case", "behavioural"]
ROUND_NAMES = {"sql": "SQL", "statistics": "Statistics", "metrics-case": "Metrics case",
               "behavioural": "Behavioural"}
SCORE_LABELS = {4: "Strong", 3: "Pass", 2: "Not yet", 1: "Below bar"}


class ProgressError(Exception):
    pass


def today():
    return datetime.date.today().isoformat()


def check_date(text):
    try:
        datetime.date.fromisoformat(text)
    except (TypeError, ValueError):
        raise ProgressError("dates look like 2026-10-31, got %r" % (text,))
    return text


# --------------------------------------------------------------------------
# Curriculum
# --------------------------------------------------------------------------

def lesson_area(phase_slug, skills):
    area = PHASE_AREA.get(phase_slug)
    if area:
        return area
    for s in skills:
        if s in SKILL_AREA:
            return SKILL_AREA[s]
    return "foundations"


def load_lessons(root=ROOT):
    """Live lessons in curriculum order, each with its phase, area and level."""
    with open(os.path.join(root, "curriculum.json"), encoding="utf-8") as f:
        cur = json.load(f)
    out = []
    for phase in cur["phases"]:
        for l in phase["lessons"]:
            if l.get("status") != "live":
                continue
            skills = l.get("skills", [])
            area = lesson_area(phase["slug"], skills)
            also = []
            for s in skills:
                a = SKILL_AREA.get(s)
                if a and a != area and a not in also:
                    also.append(a)
            out.append({"id": l["id"], "title": l["title"], "path": l["path"], "phase": phase["slug"],
                        "level": l["level"], "kind": l["kind"], "skills": skills, "area": area, "also": also})
    return out


def roadmap_order(lessons):
    """Level 1 across the phases, then Level 2, then Level 3, then Level 4 (LEARNING_ROADMAP.md)."""
    rank = dict((lv, n) for n, lv in enumerate(LEVELS))
    return sorted(lessons, key=lambda l: rank.get(l["level"], len(LEVELS)))


# --------------------------------------------------------------------------
# Profile
# --------------------------------------------------------------------------

def new_profile():
    return {"version": VERSION, "created": today(), "track": None, "fast_track": None,
            "placements": [], "attempts": [], "interviews": [], "notes": []}


def load_profile(path):
    if not os.path.exists(path):
        return new_profile()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    base = new_profile()
    base.update(data)
    return base


def save_profile(profile, path):
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# Placement
# --------------------------------------------------------------------------

def _ids(items):
    out = []
    for it in items or []:
        lid = it.get("id") if isinstance(it, dict) else it
        if isinstance(lid, str):
            out.append(lid)
    return out


def _scalars(d):
    return dict((k, v) for k, v in d.items() if isinstance(v, (str, int, float, bool)) or v is None)


def placement_entry(result, date):
    """Turn placement.py --json output into a profile entry. Reads only the JSON."""
    if not isinstance(result, dict) or "scores" not in result or "recommendation" not in result:
        raise ProgressError("not a placement result: expected the output of placement.py --json "
                            "with 'scores' and 'recommendation'")
    scores, rec = result["scores"], result["recommendation"]
    areas = {}
    for name, s in (scores.get("areas") or {}).items():
        if not isinstance(s, dict) or "correct" not in s or "total" not in s:
            raise ProgressError("placement area %s has no correct/total" % name)
        areas[name] = _scalars(s)
    if not areas:
        raise ProgressError("placement result has no areas")
    entry = {"date": date, "track": rec.get("track"), "areas": areas,
             "correct": scores.get("correct", sum(a["correct"] for a in areas.values())),
             "total": scores.get("total", sum(a["total"] for a in areas.values())),
             "beginner": rec.get("beginner"), "strong_areas": list(rec.get("strong_areas") or []),
             "start": (rec.get("start") or {}).get("id"), "path": _ids(rec.get("path")),
             "skip": _ids(rec.get("skip")), "skim": _ids(rec.get("skim"))}
    # Levels, if this version of placement.py reports them (per area or as a block).
    for holder in (scores, rec, result):
        if isinstance(holder.get("levels"), dict):
            entry["levels"] = holder["levels"]
            break
    return entry


def record_placement(profile, result, date):
    entry = placement_entry(result, date)
    profile["placements"].append(entry)
    if entry["track"]:
        profile["track"] = entry["track"]
        profile["fast_track"] = {"track": entry["track"], "path": entry["path"], "skip": entry["skip"]}
    return entry


def run_placement(args):
    """Run placement.py with --json and return its parsed output."""
    cmd = [sys.executable, "-B", PLACEMENT] + args + ["--json"]
    proc = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, timeout=120)
    if proc.returncode != 0:
        raise ProgressError("placement.py failed: %s" % (proc.stderr.strip() or proc.stdout.strip()))
    text = proc.stdout
    try:
        return json.loads(text[text.index("{"):])
    except ValueError:
        raise ProgressError("placement.py did not print JSON")


def set_track(profile, track, profile_path):
    """Store the track and its fast-track path, read from placement.py's JSON output."""
    folder = os.path.dirname(os.path.abspath(profile_path))
    os.makedirs(folder, exist_ok=True)
    blank = os.path.join(folder, "blank_answers.json")
    with open(blank, "w", encoding="utf-8") as f:
        json.dump({"track": track, "answers": {}}, f)
    try:
        result = run_placement(["--answers", blank, "--track", track])
    finally:
        os.remove(blank)
    rec = result["recommendation"]
    profile["track"] = track
    profile["fast_track"] = {"track": track, "path": _ids(rec.get("path")), "skip": []}
    return profile["fast_track"]


# --------------------------------------------------------------------------
# Lessons
# --------------------------------------------------------------------------

def find_lesson(lessons, lid):
    for l in lessons:
        if l["id"] == lid:
            return l
    raise ProgressError("no live lesson %s in curriculum.json" % lid)


def record_attempt(profile, lid, passed, date, target="exercise"):
    entry = {"id": lid, "date": date, "passed": bool(passed), "target": target}
    profile["attempts"].append(entry)
    return entry


def run_lesson_test(lesson, use_solution=False, root=ROOT):
    """Run test_lesson.py with -B. Checks the exercise unless use_solution (tests only)."""
    ldir = os.path.join(root, lesson["path"])
    if not os.path.isfile(os.path.join(ldir, "test_lesson.py")):
        raise ProgressError("%s has no test_lesson.py" % lesson["path"])
    env = dict(os.environ)
    env.pop("CHECK_SOLUTION", None)
    if use_solution:
        env["CHECK_SOLUTION"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run([sys.executable, "-B", "test_lesson.py"], cwd=ldir, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=300)
    return proc.returncode == 0, proc.stdout


def passed_lessons(profile, since=None):
    """{lesson id: first date passed} from the learner's own work (never the solution)."""
    out = {}
    for a in sorted(profile["attempts"], key=lambda a: a["date"]):
        if a.get("passed") and a.get("target", "exercise") in ("exercise", "guide"):
            if since is None or a["date"] >= since:
                out.setdefault(a["id"], a["date"])
    return out


def in_progress(profile, passed):
    """Lessons attempted but not passed, most recent first."""
    seen, out = set(), []
    for a in sorted(profile["attempts"], key=lambda a: a["date"], reverse=True):
        if a.get("target", "exercise") == "solution":
            continue
        if a["id"] not in passed and a["id"] not in seen:
            out.append(a["id"])
        seen.add(a["id"])
    return out


# --------------------------------------------------------------------------
# Mock interviews
# --------------------------------------------------------------------------

def scorecard_template():
    rounds = {}
    for r in ROUNDS:
        rounds[r] = {"score": None, "question": "", "met_bar": "", "nudges": 0, "evidence": [], "revisit": []}
    return {"date": today(), "role": "", "rounds": rounds, "overall": "", "strongest_moment": "",
            "fix_first": "", "revisit": []}


def overall_result(scores):
    """The rubric rule: pass when at least three rounds score 3 or more and no round scores 1."""
    high = sum(1 for s in scores if s >= 3)
    return "pass" if high >= 3 and min(scores) > 1 else "not yet"


def _norm_round(name):
    key = str(name).strip().lower().replace("_", "-").replace(" ", "-")
    return {"metrics": "metrics-case", "case": "metrics-case", "behavioral": "behavioural",
            "stats": "statistics"}.get(key, key)


def interview_entry(card, lessons, date=None):
    if not isinstance(card, dict) or not isinstance(card.get("rounds"), dict):
        raise ProgressError("a scorecard needs a 'rounds' object; see interview --template")
    live = set(l["id"] for l in lessons)
    rounds = {}
    for name, r in card["rounds"].items():
        key = _norm_round(name)
        if key not in ROUNDS:
            raise ProgressError("unknown round %r; rounds are %s" % (name, ", ".join(ROUNDS)))
        if not isinstance(r, dict):
            r = {"score": r}
        score = r.get("score")
        if isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 4:
            raise ProgressError("round %s: score must be a whole number from 1 to 4, got %r" % (key, score))
        nudges = r.get("nudges", 0)
        if isinstance(nudges, str):
            nudges = int(nudges.rstrip("+") or 0)
        if nudges >= 2 and score > 2:
            raise ProgressError("round %s: two or more nudges cap the round at 2 (INTERVIEW_RUBRIC.md)" % key)
        revisit = _ids(r.get("revisit"))
        bad = [x for x in revisit if x not in live]
        if bad:
            raise ProgressError("round %s: revisit names lessons that are not live: %s" % (key, ", ".join(bad)))
        out = {"score": score, "label": SCORE_LABELS[score], "nudges": nudges, "revisit": revisit}
        for k in ("question", "met_bar", "evidence", "finished"):
            if r.get(k) not in (None, "", []):
                out[k] = r[k]
        rounds[key] = out
    missing = [r for r in ROUNDS if r not in rounds]
    if missing:
        raise ProgressError("scorecard is missing rounds: %s" % ", ".join(missing))
    overall = overall_result([rounds[r]["score"] for r in ROUNDS])
    given = str(card.get("overall") or "").strip().lower()
    if given and given != overall:
        raise ProgressError("overall says %r but the rubric rule gives %r" % (given, overall))
    revisit = []
    for x in _ids(card.get("revisit")) + [x for r in ROUNDS for x in rounds[r]["revisit"]]:
        if x not in live:
            raise ProgressError("revisit names a lesson that is not live: %s" % x)
        if x not in revisit:
            revisit.append(x)
    entry = {"date": check_date(date or card.get("date") or today()), "rounds": rounds, "overall": overall,
             "revisit": revisit}
    for k in ("role", "strongest_moment", "fix_first"):
        if card.get(k):
            entry[k] = card[k]
    return entry


# --------------------------------------------------------------------------
# Status
# --------------------------------------------------------------------------

def next_lesson(profile, lessons):
    """The next lesson and why. Order: unfinished attempt, interview revisits, track path, roadmap order."""
    by_id = dict((l["id"], l) for l in lessons)
    passed = passed_lessons(profile)

    def tested(lid):
        return lid in by_id

    for lid in in_progress(profile, passed):
        if tested(lid):
            return lid, "You started it and the test has not passed yet."
    if profile["interviews"]:
        last = profile["interviews"][-1]
        since = passed_lessons(profile, since=last["date"])
        for lid in last["revisit"]:
            if tested(lid) and lid not in since:
                return lid, "Your mock interview on %s named it to revisit." % last["date"]
    ft = profile.get("fast_track") or {}
    latest = profile["placements"][-1] if profile["placements"] else None
    path = (latest or {}).get("path") or ft.get("path") or []
    strong = set((latest or {}).get("strong_areas") or [])
    track = (latest or {}).get("track") or ft.get("track")
    if latest and latest.get("beginner") and latest.get("start") and latest["start"] not in passed:
        return latest["start"], "Your placement suggests the full path from phase 00."
    gaps = [lid for lid in path if tested(lid) and lid not in passed and by_id[lid]["area"] not in strong]
    rest = [lid for lid in path if tested(lid) and lid not in passed and lid not in gaps]
    if gaps:
        return gaps[0], "Next on the %s fast track, in an area to work on." % track
    if rest:
        return rest[0], "Next on the %s fast track (you scored well in its area: skim it)." % track
    skip = set((latest or {}).get("skip") or [])
    for l in roadmap_order(lessons):
        if l["id"] not in passed and l["id"] not in skip:
            return l["id"], "Next %s lesson in roadmap order (LEARNING_ROADMAP.md)." % l["level"]
    return None, "Every live lesson is passed."


def status(profile, lessons):
    passed = passed_lessons(profile)
    latest = profile["placements"][-1] if profile["placements"] else None
    areas = []
    for a in AREAS:
        ls = [l for l in lessons if l["area"] == a]
        if not ls:
            continue
        row = {"area": a, "name": AREA_NAMES[a], "passed": sum(1 for l in ls if l["id"] in passed),
               "total": len(ls)}
        if latest and a in latest["areas"]:
            row["placement"] = latest["areas"][a]
        areas.append(row)
    phases = []
    for slug in PHASE_AREA:
        ls = [l for l in lessons if l["phase"] == slug]
        if ls:
            phases.append({"phase": slug, "passed": sum(1 for l in ls if l["id"] in passed), "total": len(ls)})
    levels = []
    for lv in LEVELS:
        ls = [l for l in lessons if l["level"] == lv]
        levels.append({"level": lv, "passed": sum(1 for l in ls if l["id"] in passed), "total": len(ls)})
    lid, why = next_lesson(profile, lessons)
    by_id = dict((l["id"], l) for l in lessons)
    nxt = None
    if lid:
        nxt = {"id": lid, "title": by_id[lid]["title"], "path": by_id[lid]["path"], "why": why}
    last_interview = profile["interviews"][-1] if profile["interviews"] else None
    return {"track": profile.get("track"), "passed": len(passed), "total": len(lessons),
            "areas": areas, "phases": phases, "levels": levels,
            "in_progress": in_progress(profile, passed), "next": nxt,
            "placement": ({"date": latest["date"], "correct": latest["correct"], "total": latest["total"]}
                          if latest else None),
            "interview": ({"date": last_interview["date"], "overall": last_interview["overall"],
                           "revisit": last_interview["revisit"]} if last_interview else None),
            "notes": len(profile["notes"])}


def _frac(p, t):
    return "%d / %d" % (p, t)


def _bar(p, t, width=10):
    n = int(round(width * p / t)) if t else 0
    return "[" + "#" * n + "." * (width - n) + "]"


def format_status(st):
    out = ["Learner profile", "", "Track: %s" % (st["track"] or "not set (run placement or `progress.py track`)"),
           "Lessons passed: %s" % _frac(st["passed"], st["total"])]
    if st["placement"]:
        p = st["placement"]
        out.append("Latest placement: %s, %d / %d" % (p["date"], p["correct"], p["total"]))
    if st["interview"]:
        out.append("Latest mock interview: %s, %s" % (st["interview"]["date"], st["interview"]["overall"]))
    out += ["", "Skill map (lessons passed, and placement score where there is one):"]
    for a in st["areas"]:
        extra = ""
        if "placement" in a:
            s = a["placement"]
            extra = "  placement %d / %d" % (s["correct"], s["total"])
            if s.get("level"):
                extra += " (%s)" % s["level"]
        out.append("  %-14s %s %7s%s" % (a["name"], _bar(a["passed"], a["total"]), _frac(a["passed"], a["total"]),
                                         extra))
    out += ["", "By level:"]
    for lv in st["levels"]:
        out.append("  %-14s %s %7s" % (lv["level"], _bar(lv["passed"], lv["total"]), _frac(lv["passed"], lv["total"])))
    out += ["", "By phase:"]
    for ph in st["phases"]:
        out.append("  %-34s %7s" % (ph["phase"], _frac(ph["passed"], ph["total"])))
    if st["in_progress"]:
        out += ["", "Started, not passed yet: %s" % ", ".join(st["in_progress"])]
    out.append("")
    if st["next"]:
        n = st["next"]
        out += ["Next: %s %s" % (n["id"], n["title"]), "  %s/" % n["path"], "  %s" % n["why"],
                "  When you are done: python3 tools/progress.py check %s" % n["id"]]
    else:
        out.append("Next: every live lesson is passed.")
    return "\n".join(out)


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------

def _pct(c, t):
    return int(round(100.0 * c / t)) if t else 0


def report(profile, lessons):
    pl = profile["placements"]
    placement = None
    if pl:
        first, last = pl[0], pl[-1]
        rows = []
        for a in [x for x in PLACEMENT_AREAS if x in first["areas"] or x in last["areas"]] + \
                sorted((set(first["areas"]) | set(last["areas"])) - set(PLACEMENT_AREAS)):
            f, l = first["areas"].get(a), last["areas"].get(a)
            row = {"area": a, "name": AREA_NAMES.get(a, a), "first": f, "latest": l}
            if f and l:
                row["change_pct"] = _pct(l["correct"], l["total"]) - _pct(f["correct"], f["total"])
            rows.append(row)
        placement = {"count": len(pl), "first_date": first["date"], "latest_date": last["date"],
                     "first_total": [first["correct"], first["total"]],
                     "latest_total": [last["correct"], last["total"]], "areas": rows}
    passed = passed_lessons(profile)
    by_date = {}
    for lid, d in passed.items():
        by_date.setdefault(d, []).append(lid)
    timeline, running = [], 0
    for d in sorted(by_date):
        running += len(by_date[d])
        timeline.append({"date": d, "passed": sorted(by_date[d]), "cumulative": running})
    by_id = dict((l["id"], l) for l in lessons)
    area_counts = {}
    for lid in passed:
        if lid in by_id:
            a = by_id[lid]["area"]
            area_counts[a] = area_counts.get(a, 0) + 1
    interviews = [{"date": i["date"], "scores": dict((r, i["rounds"][r]["score"]) for r in ROUNDS),
                   "overall": i["overall"], "revisit": i["revisit"]} for i in profile["interviews"]]
    return {"track": profile.get("track"), "placement": placement, "lessons": {
        "passed": len(passed), "total": len(lessons), "timeline": timeline,
        "by_area": [{"area": a, "name": AREA_NAMES[a], "passed": area_counts.get(a, 0),
                     "total": sum(1 for l in lessons if l["area"] == a)} for a in AREAS
                    if any(l["area"] == a for l in lessons)]},
        "interviews": interviews, "notes": profile["notes"]}


def _score(s):
    if not s:
        return "-"
    text = "%d / %d" % (s["correct"], s["total"])
    return text + (" (%s)" % s["level"] if s.get("level") else "")


def format_report(rep, md=False):
    h1, h2 = ("# ", "## ") if md else ("", "")
    out = [h1 + "Learning progress", ""]
    out.append("Track: %s. Every number here comes from my own placement checks, lesson tests and mock "
               "interview scorecards in Analytics from Scratch." % (rep["track"] or "not set"))
    out += ["", h2 + "Placement: first and latest", ""]
    p = rep["placement"]
    if not p:
        out.append("No placement recorded yet.")
    else:
        if p["count"] == 1:
            out.append("One placement so far (%s). Run it again later to see the change." % p["first_date"])
        else:
            out.append("First %s, latest %s (%d placements)." % (p["first_date"], p["latest_date"], p["count"]))
        out.append("")
        rows = [("Area", "First", "Latest", "Change")]
        for r in p["areas"]:
            ch = "-" if "change_pct" not in r else "%+d points" % r["change_pct"]
            rows.append((r["name"], _score(r["first"]), _score(r["latest"]), ch))
        rows.append(("Total", "%d / %d" % tuple(p["first_total"]), "%d / %d" % tuple(p["latest_total"]), ""))
        out += _table(rows, md)
    L = rep["lessons"]
    out += ["", h2 + "Lessons passed over time", "",
            "%d of %d live lessons passed, each by its own test on my exercise." % (L["passed"], L["total"]), ""]
    if L["timeline"]:
        rows = [("Date", "Passed that day", "Total so far")]
        for t in L["timeline"]:
            rows.append((t["date"], ", ".join(t["passed"]), str(t["cumulative"])))
        out += _table(rows, md)
        out.append("")
        rows = [("Area", "Passed")] + [(a["name"], "%d / %d" % (a["passed"], a["total"])) for a in L["by_area"]
                                       if a["passed"]]
        out += _table(rows, md)
    else:
        out.append("No lessons passed yet.")
    out += ["", h2 + "Mock interviews over time", ""]
    if rep["interviews"]:
        rows = [("Date",) + tuple(ROUND_NAMES[r] for r in ROUNDS) + ("Overall",)]
        for i in rep["interviews"]:
            rows.append((i["date"],) + tuple("%d / 4" % i["scores"][r] for r in ROUNDS) + (i["overall"],))
        out += _table(rows, md)
        out += ["", "Scored 1 to 4 per round against the course's interview rubric. A practice mock, "
                    "not a prediction of a real interview."]
    else:
        out.append("No mock interviews recorded yet.")
    return "\n".join(out) + "\n"


def _table(rows, md):
    if md:
        out = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(rows[0])]
        return out + ["| " + " | ".join(r) + " |" for r in rows[1:]]
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    return ["  " + "  ".join(c.ljust(w) for c, w in zip(r, widths)).rstrip() for r in rows]


# --------------------------------------------------------------------------
# Pilot export (opt-in) and aggregate
# --------------------------------------------------------------------------
#
# Nothing here runs unless the learner types `export`. An export is pseudonymous, not
# anonymous: it has no name or contact details, but an id and an activity pattern could
# still point to one person in a small group. So there are two levels:
#
#   coarse (the default): no lasting id (a fresh random export_id each time, only so the
#     same file pasted twice counts once), the ISO week of the export, days counted from
#     the first day of activity instead of dates, lesson ids with passed or not, placement
#     levels only, interview pass or not per round, and the course month.
#   full: a random pilot_id kept in the profile, day dates, tries per lesson, placement
#     scores, 1 to 4 interview scores and the course commit. Meant to be sent privately
#     to the pilot organiser, not posted in public.
#
# Both are built from an allowlist: every value is a number, a day count or date, a lesson
# id, an area or round name, a level word or a random id. Notes, names, paths, scorecard
# text and any other free text are never copied. EXPORT_KEYS and COARSE_KEYS are the full
# schemas and test_progress.py fails if a key outside the level's allowlist appears.

EXPORT_LEVELS = ["coarse", "full"]
DEFAULT_EXPORT_LEVEL = "coarse"
EXPORT_SCHEMA = "afs-pilot-export-1"            # full
COARSE_SCHEMA = "afs-pilot-export-coarse-1"     # coarse
EXPORT_KEYS = {
    "top": ["schema", "pilot_id", "exported_on", "course_version", "track", "placement", "lessons",
            "activity", "interviews"],
    "placement": ["count", "first", "latest"],
    "placement_entry": ["date", "correct", "total", "areas"],
    "placement_area": ["correct", "total", "level"],
    "lessons": ["attempted", "passed", "items"],
    "lesson_item": ["id", "first_attempt", "attempts", "passed", "passed_on", "attempts_before_pass"],
    "activity": ["first_day", "latest_day", "days_between"],
    "interview": ["date", "scores", "overall"],
}
COARSE_KEYS = {
    "top": ["schema", "export_id", "exported_week", "course_month", "track", "placement", "lessons",
            "activity", "interviews"],
    "placement": ["count", "first", "latest"],          # first and latest: {area: level}
    "lessons": ["attempted", "passed", "items"],
    "lesson_item": ["id", "passed"],
    "activity": ["latest_day", "export_day", "first_pass_day"],
    "interview": ["rounds", "overall"],                  # rounds: {round: passed true or false}
}
ALLOWLISTS = {"full": EXPORT_KEYS, "coarse": COARSE_KEYS}
SCHEMA_LEVEL = {EXPORT_SCHEMA: "full", COARSE_SCHEMA: "coarse"}

PSEUDONYMOUS = ("Pseudonymous means: no name or contact details, but a random id and your\n"
                "activity pattern could still point to you in a small group.")
PUBLIC_WARNING = ("A GitHub issue on a public repo is visible to everyone, and copies can outlive\n"
                  "an edit or a deletion. If you prefer, send the export privately to the pilot\n"
                  "organiser instead of pasting it in an issue. For anything public, use the\n"
                  "coarse level (the default).")
NEVER = ("It never includes your notes, names, emails, file paths, placement answers,\n"
         "interview questions or comments, or any other text you typed.\n")

EXPORT_NOTICE = """This makes a pseudonymous summary of your progress (level: full) that you can
choose to share. Nothing is sent anywhere.
%s

%s

It includes ONLY:
  - schema: the format name, %s
  - pilot_id: a random id kept in your profile, not made from anything about you,
    so your exports line up over time (make a new one with: export --new-id)
  - exported_on: today's date (day only)
  - course_version: the git commit of this copy of the course, or "unknown"
  - track: your goal, such as data-analyst, or null
  - placement: how many placements, then the first and latest one: date (day only),
    total correct and per area (sql, statistics, ...) correct, total and level
  - lessons: for each lesson you tried: its id, the day of the first try, number of
    tries, passed or not, the day it passed and the failed tries before the pass
  - activity: your first and latest day of activity and the days between them
  - interviews: for each mock interview: date (day only), the 1 to 4 score per round
    and pass or not yet

%s""" % (PSEUDONYMOUS, PUBLIC_WARNING, EXPORT_SCHEMA, NEVER)

COARSE_NOTICE = """This makes a pseudonymous summary of your progress (level: coarse) that you can
choose to share. Nothing is sent anywhere.
%s
The coarse level leaves out dates, tries and scores to lower that risk.

%s

It includes ONLY:
  - schema: the format name, %s
  - export_id: a new random id made for this export only and not stored anywhere,
    so two exports from you cannot be linked by it
  - exported_week: the ISO week of today, such as 2026-W44 (no day)
  - course_month: the month of this copy of the course, such as 2026-10, or "unknown"
  - track: your goal, such as data-analyst, or null
  - placement: how many placements, then the level (strong, mixed or weak) per area
    for the first and latest one (no scores, no dates)
  - lessons: for each lesson you tried: its id and passed or not (no tries, no dates)
  - activity: counted in days since your first day of activity (day 0): your latest
    day of activity, today, and the day you first passed a lesson (or null)
  - interviews: for each mock interview: passed or not per round, and pass or not yet
    overall (no 1 to 4 scores, no dates)

%s""" % (PSEUDONYMOUS, PUBLIC_WARNING, COARSE_SCHEMA, NEVER)

NOTICES = {"full": EXPORT_NOTICE, "coarse": COARSE_NOTICE}

_ID_RE = re.compile(r"^\d\d-\d\d$")
_WORD_RE = re.compile(r"^[a-z][a-z0-9-]{0,39}$")
_PILOT_RE = re.compile(r"^p-[0-9a-f]{16}$")
_EXPORT_ID_RE = re.compile(r"^x-[0-9a-f]{16}$")
_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
_WEEK_RE = re.compile(r"^\d{4}-W\d{2}$")
PLACEMENT_LEVELS = ["strong", "mixed", "weak"]
ROUND_PASS = 3   # a round scoring 3 or 4 meets the bar (INTERVIEW_RUBRIC.md)


def new_pilot_id():
    import secrets
    return "p-" + secrets.token_hex(8)


def new_export_id():
    import secrets
    return "x-" + secrets.token_hex(8)


def _git(args, root):
    try:
        proc = subprocess.run(["git"] + args, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              universal_newlines=True, timeout=10)
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception:
        pass
    return ""


def course_version(root=ROOT):
    """The git short sha of this copy, or "unknown". Never raises."""
    sha = _git(["rev-parse", "--short", "HEAD"], root)
    return sha if _SHA_RE.match(sha) else "unknown"


def course_month(root=ROOT):
    """The month (YYYY-MM) of this copy's latest commit, or "unknown". Never raises."""
    month = _git(["log", "-1", "--date=short", "--format=%cd"], root)[:7]
    return month if _MONTH_RE.match(month) else "unknown"


def _day(value):
    """A YYYY-MM-DD day, or None. Anything longer is cut to the day."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return None


def _iso_week(day):
    y, w = datetime.date.fromisoformat(day).isocalendar()[:2]
    return "%04d-W%02d" % (y, w)


def _int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _word(value, allowed=None):
    if not isinstance(value, str) or not _WORD_RE.match(value):
        return None
    if allowed is not None and value not in allowed:
        return None
    return value


def _export_placement(entry):
    areas = {}
    for name, s in sorted((entry.get("areas") or {}).items()):
        if not _word(name) or not isinstance(s, dict):
            continue
        areas[name] = {"correct": _int(s.get("correct")), "total": _int(s.get("total")),
                       "level": _word(s.get("level"), PLACEMENT_LEVELS)}
    return {"date": _day(entry.get("date")), "correct": _int(entry.get("correct")),
            "total": _int(entry.get("total")), "areas": areas}


def export_summary(profile, lessons=None, version=None, on=None):
    """The full pseudonymous pilot summary. Builds every value from scratch (an allowlist)."""
    live = set(l["id"] for l in lessons) if lessons else None
    placements = [p for p in profile.get("placements") or [] if isinstance(p, dict)]
    placement = None
    if placements:
        placement = {"count": len(placements), "first": _export_placement(placements[0]),
                     "latest": _export_placement(placements[-1])}
    per = {}
    attempts = [a for a in profile.get("attempts") or [] if isinstance(a, dict)]
    for a in sorted(attempts, key=lambda a: str(a.get("date"))):
        lid, day = a.get("id"), _day(a.get("date"))
        if a.get("target", "exercise") not in ("exercise", "guide") or not isinstance(lid, str) or not day:
            continue
        if not _ID_RE.match(lid) or (live is not None and lid not in live):
            continue
        it = per.setdefault(lid, {"id": lid, "first_attempt": day, "attempts": 0, "passed": False,
                                  "passed_on": None, "attempts_before_pass": None})
        it["attempts"] += 1
        if a.get("passed") and not it["passed"]:
            it["passed"], it["passed_on"], it["attempts_before_pass"] = True, day, it["attempts"] - 1
    items = [per[k] for k in sorted(per)]
    interviews = []
    for i in profile.get("interviews") or []:
        if not isinstance(i, dict):
            continue
        rounds = i.get("rounds") or {}
        scores = dict((r, _int((rounds.get(r) or {}).get("score"))) for r in ROUNDS)
        overall = i.get("overall") if i.get("overall") in ("pass", "not yet") else None
        interviews.append({"date": _day(i.get("date")), "scores": scores, "overall": overall})
    days = [_day(p.get("date")) for p in placements] + [x["date"] for x in interviews]
    days += [_day(a.get("date")) for a in attempts if a.get("target", "exercise") != "solution"]
    days = [d for d in days if d]
    activity = {"first_day": None, "latest_day": None, "days_between": None}
    if days:
        lo, hi = min(days), max(days)
        activity = {"first_day": lo, "latest_day": hi, "days_between": _days(lo, hi)}
    pid = profile.get("pilot_id")
    return {"schema": EXPORT_SCHEMA,
            "pilot_id": pid if isinstance(pid, str) and _PILOT_RE.match(pid) else None,
            "exported_on": _day(on) or today(),
            "course_version": version if isinstance(version, str) and _SHA_RE.match(version) else "unknown",
            "track": _word(profile.get("track")),
            "placement": placement,
            "lessons": {"attempted": len(items), "passed": sum(1 for x in items if x["passed"]), "items": items},
            "activity": activity, "interviews": interviews}


def coarse_summary(profile, lessons=None, month=None, on=None):
    """The coarse pseudonymous summary, made from the full one by dropping detail.

    No lasting id, no day dates (days since the first day of activity instead, and the
    ISO week of the export), passed or not per lesson, placement levels only, interview
    pass or not per round, and the course month."""
    full = export_summary(profile, lessons, on=on)
    act = full["activity"]
    first = act["first_day"]

    def since(day):
        return _days(first, day) if first and day else None

    placement = None
    if full["placement"]:
        p = full["placement"]
        placement = {"count": p["count"]}
        for which in ("first", "latest"):
            placement[which] = dict((a, v["level"]) for a, v in p[which]["areas"].items())
    items = [{"id": x["id"], "passed": x["passed"]} for x in full["lessons"]["items"]]
    pass_days = [x["passed_on"] for x in full["lessons"]["items"] if x["passed_on"]]
    interviews = []
    for i in full["interviews"]:
        rounds = dict((r, (s >= ROUND_PASS) if s is not None else None) for r, s in i["scores"].items())
        interviews.append({"rounds": rounds, "overall": i["overall"]})
    return {"schema": COARSE_SCHEMA,
            "export_id": new_export_id(),
            "exported_week": _iso_week(full["exported_on"]),
            "course_month": month if isinstance(month, str) and _MONTH_RE.match(month) else "unknown",
            "track": full["track"],
            "placement": placement,
            "lessons": {"attempted": len(items), "passed": sum(1 for x in items if x["passed"]), "items": items},
            "activity": {"latest_day": since(act["latest_day"]), "export_day": since(full["exported_on"]),
                         "first_pass_day": since(min(pass_days)) if pass_days else None},
            "interviews": interviews}


def _confirm(assume_yes, stdin=None):
    """True with --yes, or after an interactive y. Never waits when stdin is not a terminal."""
    if assume_yes:
        return True
    stdin = stdin or sys.stdin
    try:
        interactive = stdin.isatty()
    except (AttributeError, ValueError):
        interactive = False
    if not interactive:
        sys.stderr.write("Nothing written. Read the list above, then run again with --yes to confirm.\n")
        return False
    sys.stderr.write("Write this summary? Type y to confirm: ")
    sys.stderr.flush()
    answer = stdin.readline().strip().lower()
    if answer not in ("y", "yes"):
        sys.stderr.write("Nothing written.\n")
        return False
    return True


def _median(values):
    vals = sorted(values)
    if not vals:
        return None
    mid = len(vals) // 2
    return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2.0


def _days(a, b):
    return (datetime.date.fromisoformat(b) - datetime.date.fromisoformat(a)).days


def export_level(data):
    """The level of a pilot export: full, coarse, or None when it is not one."""
    return SCHEMA_LEVEL.get(data.get("schema")) if isinstance(data, dict) else None


def load_exports(folder):
    """Every pilot export (*.json) in a folder, full and coarse.

    Full exports: one per pilot id, the latest export wins. Coarse exports have no lasting
    id, so they cannot be linked: each distinct export_id counts once (the same file saved
    twice counts once, but two coarse exports from one learner count twice)."""
    by_id, skipped = {}, []
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(folder, name), encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            skipped.append(name)
            continue
        level = export_level(data)
        if level is None:
            skipped.append(name)
            continue
        if level == "full":
            key = "full:" + (data.get("pilot_id") or name)
            stamp = data.get("exported_on") or ""
        else:
            key = "coarse:" + (data.get("export_id") or name)
            stamp = ""
        old = by_id.get(key)
        if old is None or stamp >= (old[0] or ""):
            by_id[key] = (stamp, data)
    return [by_id[k][1] for k in sorted(by_id)], skipped


def _learner_view(e):
    """What aggregate needs from one export, the same for both levels. None means not in this export."""
    level = export_level(e)
    lessons = e.get("lessons") or {}
    items = [x for x in lessons.get("items") or [] if isinstance(x, dict) and isinstance(x.get("id"), str)]
    act = e.get("activity") or {}
    pl = e.get("placement") or None
    v = {"level": level, "placed": bool(pl), "passed": lessons.get("passed") or 0, "items": items,
         "first_pass_day": None, "latest_day": None, "export_day": None,
         "placement_count": (pl or {}).get("count", 0), "levels_first": {}, "levels_latest": {},
         "points": None, "interviews": e.get("interviews") or []}
    if level == "full":
        first = act.get("first_day")
        if first:
            days = [x["passed_on"] for x in items if x.get("passed_on")]
            v["first_pass_day"] = _days(first, min(days)) if days else None
            v["latest_day"] = _days(first, act["latest_day"]) if act.get("latest_day") else None
            v["export_day"] = _days(first, e["exported_on"]) if e.get("exported_on") else None
        if pl:
            v["levels_first"] = dict((a, s.get("level")) for a, s in (pl["first"].get("areas") or {}).items())
            v["levels_latest"] = dict((a, s.get("level")) for a, s in (pl["latest"].get("areas") or {}).items())
            v["points"] = (pl["first"], pl["latest"])
    else:
        for k in ("first_pass_day", "latest_day", "export_day"):
            v[k] = _int(act.get(k))
        if pl:
            v["levels_first"] = dict(pl.get("first") or {})
            v["levels_latest"] = dict(pl.get("latest") or {})
    return v


COARSE_GAPS = [
    "placement change in points: coarse exports have levels only, so placement_before_after uses full "
    "exports only; placement_level_change counts both",
    "median failed tries before a pass (where people get stuck): full exports only; coarse keeps passed "
    "or not per lesson",
    "one count per learner: coarse exports have no lasting id, so a learner who sent several coarse "
    "exports, or a full and a coarse one, is counted more than once",
]


def aggregate(exports, day7=7):
    """Pilot metrics from many exports, full and coarse. Each metric says what it is out of."""
    views = [_learner_view(e) for e in exports]
    n = len(views)
    n_coarse = sum(1 for v in views if v["level"] == "coarse")
    placed = [v for v in views if v["placed"]]
    passers = [v for v in views if v["passed"]]
    first_pass_days = [v["first_pass_day"] for v in passers if v["first_pass_day"] is not None]
    # Day-7 return: some activity on or after day 7, among learners whose export is at least 7 days
    # after their first day (so the question can be answered). Both levels count days from day 0.
    eligible, returned = 0, 0
    for v in views:
        if v["export_day"] is None or v["latest_day"] is None:
            continue
        if v["export_day"] >= day7:
            eligible += 1
            if v["latest_day"] >= day7:
                returned += 1
    per_learner = [v["passed"] for v in views]
    before_after = {}
    repeat_full = [v for v in views if v["points"] and v["placement_count"] >= 2]
    for v in repeat_full:
        f, l = v["points"]
        for area in sorted(set(f.get("areas") or {}) & set(l.get("areas") or {})):
            a, b = f["areas"][area], l["areas"][area]
            if a.get("total") and b.get("total"):
                change = 100.0 * b["correct"] / b["total"] - 100.0 * a["correct"] / a["total"]
                before_after.setdefault(area, []).append(change)
    rank = {"weak": 0, "mixed": 1, "strong": 2}
    level_change = {}
    repeat_any = [v for v in views if v["placement_count"] >= 2]
    for v in repeat_any:
        for area in sorted(set(v["levels_first"]) & set(v["levels_latest"])):
            a, b = rank.get(v["levels_first"][area]), rank.get(v["levels_latest"][area])
            if a is None or b is None:
                continue
            row = level_change.setdefault(area, {"up": 0, "same": 0, "down": 0})
            row["up" if b > a else "down" if b < a else "same"] += 1
    capstone = [v for v in views if any(x.get("passed") and x["id"].startswith("10-") for x in v["items"])]
    stuck = {}
    for v in views:
        for x in v["items"]:
            s = stuck.setdefault(x["id"], {"tried": 0, "not_passed": 0, "failed": []})
            s["tried"] += 1
            if not x.get("passed"):
                s["not_passed"] += 1
            elif x.get("attempts_before_pass") is not None:
                s["failed"].append(x["attempts_before_pass"])
    stuck_rows = [{"id": k, "tried": s["tried"], "not_passed": s["not_passed"],
                   "median_failed_tries_before_pass": _median(s["failed"])} for k, s in stuck.items()]
    stuck_rows.sort(key=lambda r: (-r["not_passed"], -(r["median_failed_tries_before_pass"] or 0), r["id"]))
    interviewed = [v for v in views if v["interviews"]]
    return {
        "learners": n,
        "exports_by_level": {"full": n - n_coarse, "coarse": n_coarse},
        "placement_completed": len(placed),
        "first_lesson_passed": len(passers),
        "median_days_to_first_pass": _median(first_pass_days),
        "day7_return": {"returned": returned, "eligible": eligible},
        "lessons_passed_per_learner": {"median": _median(per_learner), "min": min(per_learner) if n else None,
                                       "max": max(per_learner) if n else None},
        "placement_before_after": {"learners_with_two_or_more": len(repeat_full), "median_change_points_by_area":
                                   dict((a, _median(x)) for a, x in sorted(before_after.items()))},
        "placement_level_change": {"learners_with_two_or_more": len(repeat_any),
                                   "by_area": dict(sorted(level_change.items()))},
        "capstone_passed": len(capstone),
        "mock_interview": {"learners": len(interviewed),
                           "latest_pass": sum(1 for v in interviewed if v["interviews"][-1].get("overall") == "pass")},
        "where_stuck": stuck_rows[:10],
        "not_available_from_coarse": list(COARSE_GAPS) if n_coarse else [],
    }


def _dash(value):
    return "-" if value is None else value


def format_aggregate(agg, skipped):
    n = agg["learners"]

    def of(k):
        return "%d of %d" % (k, n)

    out = ["Pilot metrics from %d learner export%s" % (n, "" if n == 1 else "s")]
    if skipped:
        out.append("Skipped (not a pilot export): %s" % ", ".join(skipped))
    if not n:
        return "\n".join(out + ["No exports to count."])
    lv = agg["exports_by_level"]
    d7 = agg["day7_return"]
    lp = agg["lessons_passed_per_learner"]
    ba = agg["placement_before_after"]
    lc = agg["placement_level_change"]
    out += ["Levels: %d full, %d coarse" % (lv["full"], lv["coarse"]),
            "",
            "Placement completed:        %s" % of(agg["placement_completed"]),
            "Passed a first lesson:      %s (median days from first activity: %s)"
            % (of(agg["first_lesson_passed"]), _dash(agg["median_days_to_first_pass"])),
            "Day-7 return:               %d of %d (only learners whose export is 7+ days after their first day)"
            % (d7["returned"], d7["eligible"]),
            "Lessons passed per learner: median %s, min %s, max %s" % (_dash(lp["median"]), lp["min"], lp["max"]),
            "Passed a capstone lesson:   %s" % of(agg["capstone_passed"]),
            "Mock interviews:            %d learners, %d passed their latest"
            % (agg["mock_interview"]["learners"], agg["mock_interview"]["latest_pass"]),
            "",
            "Placement first vs latest (%d full exports with two or more placements), median change in points:"
            % ba["learners_with_two_or_more"]]
    for area, ch in ba["median_change_points_by_area"].items():
        out.append("  %-12s %+.0f" % (area, ch))
    out.append("Placement level first vs latest (%d exports of either level with two or more placements):"
               % lc["learners_with_two_or_more"])
    for area, row in lc["by_area"].items():
        out.append("  %-12s up %d, same %d, down %d" % (area, row["up"], row["same"], row["down"]))
    out += ["", "Where people get stuck (lessons tried, not passed, median failed tries before a pass):"]
    for r in agg["where_stuck"]:
        m = r["median_failed_tries_before_pass"]
        out.append("  %s  tried %d, not passed %d, median failed tries %s"
                   % (r["id"], r["tried"], r["not_passed"], _dash(m)))
    if agg["not_available_from_coarse"]:
        out += ["", "Not available from coarse exports:"]
        out += ["  - " + line for line in agg["not_available_from_coarse"]]
    return "\n".join(out)


def run_export(args, profile, path, lessons):
    level = args.level
    if level == "full":
        if args.new_id or not (isinstance(profile.get("pilot_id"), str) and _PILOT_RE.match(profile["pilot_id"])):
            profile["pilot_id"] = new_pilot_id()
        summary = export_summary(profile, lessons, version=course_version())
        who = "pilot id %s" % summary["pilot_id"]
    else:
        summary = coarse_summary(profile, lessons, month=course_month())
        who = "no lasting id"
    sys.stderr.write(NOTICES[level])
    if level == "coarse" and args.new_id:
        sys.stderr.write("\n(--new-id only matters for --level full; coarse never keeps an id.)\n")
    sys.stderr.write("\nYour summary (%s): %s, %d placement(s), %d lesson(s) tried, %d passed, "
                     "%d mock interview(s).\nIt will be written to %s.\n\n"
                     % (level, who, (summary["placement"] or {}).get("count", 0),
                        summary["lessons"]["attempted"], summary["lessons"]["passed"], len(summary["interviews"]),
                        "the file you named" if args.out else "the screen (stdout)"))
    if not _confirm(args.yes):
        return 1
    if level == "full":
        save_profile(profile, path)   # keeps the pilot id, so later full exports from you line up
    text = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        sys.stderr.write("Wrote %s. Look it over, then share it only if you want to.\n" % args.out)
    else:
        sys.stdout.write(text)
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as exc:
        raise ProgressError("cannot read %s: %s" % (path, exc))


def build_parser():
    parser = argparse.ArgumentParser(description="One learner profile for every tutor mode.")
    parser.add_argument("--profile", default=DEFAULT_PROFILE, help="profile file (default .learner/profile.json)")
    sub = parser.add_subparsers(dest="command")

    s = sub.add_parser("status", help="skill map and the next lesson")
    s.add_argument("--json", action="store_true")

    c = sub.add_parser("check", help="run a lesson's test on your exercise and record the result")
    c.add_argument("lesson")
    c.add_argument("--date", help="record under this date (YYYY-MM-DD) instead of today")
    c.add_argument("--self-check", action="store_true",
                   help="guide lessons only: record that you answered its Check yourself questions")
    c.add_argument("--use-solution", action="store_true", help=argparse.SUPPRESS)  # for test_progress.py only
    c.add_argument("--quiet", action="store_true", help="do not print the test output")

    p = sub.add_parser("placement", help="record a placement result")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--from", dest="from_file", help="a file holding placement.py --json output")
    g.add_argument("--answers", help="an answers file: grade it with placement.py and record the result")
    p.add_argument("--track", help="passed to placement.py with --answers")
    p.add_argument("--date", help="record under this date instead of today")

    t = sub.add_parser("track", help="set your goal (a placement.py track)")
    t.add_argument("name")

    i = sub.add_parser("interview", help="record a mock interview scorecard")
    gi = i.add_mutually_exclusive_group(required=True)
    gi.add_argument("--from", dest="from_file", help="a scorecard JSON file")
    gi.add_argument("--template", action="store_true", help="print an empty scorecard and exit")
    i.add_argument("--date", help="record under this date instead of the card's date")

    n = sub.add_parser("note", help="add a short note")
    n.add_argument("text")
    n.add_argument("--date")

    r = sub.add_parser("report", help="before and after: placement, lessons and interviews over time")
    fmt = r.add_mutually_exclusive_group()
    fmt.add_argument("--json", action="store_true")
    fmt.add_argument("--md", action="store_true", help="Markdown, for a portfolio")

    e = sub.add_parser("export", help="opt-in: a pseudonymous summary you can choose to share with a pilot")
    e.add_argument("--level", choices=EXPORT_LEVELS, default=DEFAULT_EXPORT_LEVEL,
                   help="coarse (default): no dates, tries or scores, safer to post. "
                        "full: more detail, send it privately to the pilot organiser")
    e.add_argument("--out", help="write to this file instead of the screen")
    e.add_argument("--yes", action="store_true", help="confirm after reading the notice (needed when not typing)")
    e.add_argument("--new-id", action="store_true", help="--level full only: make a new random pilot id first")

    ag = sub.add_parser("aggregate", help="for a pilot owner: metrics from a folder of export files (both levels)")
    ag.add_argument("folder")
    ag.add_argument("--json", action="store_true")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not args.command:
        args.command, args.json = "status", False
    try:
        return _run(args)
    except ProgressError as exc:
        sys.stderr.write("progress.py: %s\n" % exc)
        return 2


def _run(args):
    if args.command == "aggregate":
        if not os.path.isdir(args.folder):
            raise ProgressError("not a folder: %s" % args.folder)
        exports, skipped = load_exports(args.folder)
        agg = aggregate(exports)
        print(json.dumps(dict(agg, skipped=skipped), indent=2) if args.json else format_aggregate(agg, skipped))
        return 0
    path = os.path.abspath(args.profile)
    lessons = load_lessons()
    profile = load_profile(path)
    date = getattr(args, "date", None)
    date = check_date(date) if date else today()

    if args.command == "status":
        st = status(profile, lessons)
        if not os.path.exists(path):
            save_profile(profile, path)
        print(json.dumps(st, indent=2) if args.json else format_status(st))
        return 0

    if args.command == "check":
        lesson = find_lesson(lessons, args.lesson)
        if lesson["kind"] == "guide":
            if not args.self_check:
                print("%s is a guide lesson, so it has no test. Answer its Check yourself questions, then run:\n"
                      "  python3 tools/progress.py check %s --self-check" % (lesson["id"], lesson["id"]))
                return 1
            record_attempt(profile, lesson["id"], True, date, target="guide")
            save_profile(profile, path)
            print("Recorded %s %s as done (guide lesson, Check yourself answered)." % (lesson["id"], lesson["title"]))
            return 0
        ok, output = run_lesson_test(lesson, use_solution=args.use_solution)
        record_attempt(profile, lesson["id"], ok, date, target="solution" if args.use_solution else "exercise")
        save_profile(profile, path)
        if not args.quiet:
            lines = output.rstrip().splitlines()
            print("\n".join(lines[-25:]))
            print("")
        if ok:
            print("PASS %s %s. Recorded. Next: python3 tools/progress.py status" % (lesson["id"], lesson["title"]))
        else:
            print("NOT YET %s %s. Recorded the attempt. Read the first failing check above, fix "
                  "%s/exercise file, and run this again." % (lesson["id"], lesson["title"], lesson["path"]))
        return 0 if ok else 1

    if args.command == "placement":
        if args.from_file:
            result = _read_json(args.from_file)
        elif args.answers:
            extra = ["--track", args.track] if args.track else []
            result = run_placement(["--answers", args.answers] + extra)
        else:
            folder = os.path.dirname(path)
            os.makedirs(folder, exist_ok=True)
            answers = os.path.join(folder, "placement_answers.json")
            if not os.path.exists(answers):
                tmpl = run_placement_template()
                with open(answers, "w", encoding="utf-8") as f:
                    f.write(tmpl)
            print("Fill in your answers in %s (the questions are in python3 tools/placement.py), then run:\n"
                  "  python3 tools/progress.py placement --answers %s\n"
                  "Or run python3 tools/placement.py --json > result.json yourself and record it with "
                  "--from result.json." % (answers, answers))
            return 0
        entry = record_placement(profile, result, date)
        save_profile(profile, path)
        print("Recorded placement on %s: %d / %d, track %s. Strong areas: %s."
              % (entry["date"], entry["correct"], entry["total"], entry["track"],
                 ", ".join(entry["strong_areas"]) or "none yet"))
        return 0

    if args.command == "track":
        ft = set_track(profile, args.name, path)
        save_profile(profile, path)
        print("Track set to %s. Fast track path: %s" % (args.name, ", ".join(ft["path"])))
        return 0

    if args.command == "interview":
        if args.template:
            print(json.dumps(scorecard_template(), indent=2))
            return 0
        entry = interview_entry(_read_json(args.from_file), lessons, args.date)
        profile["interviews"].append(entry)
        save_profile(profile, path)
        print("Recorded mock interview on %s: %s (%s). Revisit: %s"
              % (entry["date"], ", ".join("%s %d" % (ROUND_NAMES[r], entry["rounds"][r]["score"]) for r in ROUNDS),
                 entry["overall"], ", ".join(entry["revisit"]) or "nothing named"))
        return 0

    if args.command == "note":
        profile["notes"].append({"date": date, "text": args.text})
        save_profile(profile, path)
        print("Noted.")
        return 0

    if args.command == "report":
        rep = report(profile, lessons)
        print(json.dumps(rep, indent=2) if args.json else format_report(rep, md=args.md).rstrip("\n"))
        return 0

    if args.command == "export":
        return run_export(args, profile, path, lessons)
    return 2


def run_placement_template():
    proc = subprocess.run([sys.executable, "-B", PLACEMENT, "--template"], cwd=ROOT, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True, timeout=60)
    if proc.returncode != 0:
        raise ProgressError("placement.py --template failed: %s" % proc.stderr.strip())
    return proc.stdout


if __name__ == "__main__":
    sys.exit(main())
