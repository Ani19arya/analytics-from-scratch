"""Build the Bramblequay Bikes capstone data. All synthetic, and no model was called.

Tables:
- data/stations.csv: the docking stations and their zone. Station BQ13, a pop-up opened in
  September, is missing from it (the station list is maintained by hand).
- data/station_events.csv: closures. Riverside's three stations closed for roadworks in September.
- data/riders.csv: riders, with an email column the copilot must never read.
- data/rentals_raw.csv: one row per load of a rental, July to September 2026. Some rentals are
  loaded twice, the last day's rentals arrive after the snapshot, and from 16 August the app also
  logs "false starts" (unlocked and re-docked within 2 minutes), which it used to drop.

The copilot's recorded session (SIMULATED: written by this file, model "none"):
- data/plan.json: the planner's steps, each with the query agent's SQL or the check to run.
- data/approvals.csv: the human reviewer's decision on each step (approve, edit, reject).
- data/draft.json: the recommender's draft, with the step and cell each number claims to come from.
  Its numbers are computed from this seed's data, with three planted problems.

build(seed) changes the rentals and therefore every number; the plan and the approvals are the
same for every seed. Nothing is written by build(); main() writes data/.

Run: python3 make_data.py
"""
import csv
import datetime
import json
import math
import os
import random

DEFAULT_SEED = 1008
HERE = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT = "2026-10-01 00:00:00"
FALSE_STARTS_FROM = "2026-08-16"
CLOSED_FROM, CLOSED_TO = "2026-09-07", "2026-09-30"
POPUP_FROM = "2026-09-12"

STATIONS = [
    ("BQ01", "Footbridge", "Riverside", 16), ("BQ02", "Mill Steps", "Riverside", 12), ("BQ03", "Weir Lane", "Riverside", 14),
    ("BQ04", "Cornmarket", "Old Town", 18), ("BQ05", "Abbey Green", "Old Town", 12), ("BQ06", "Tanners Row", "Old Town", 10),
    ("BQ07", "Library", "University", 20), ("BQ08", "Science Park", "University", 12), ("BQ09", "Halls", "University", 14),
    ("BQ10", "Ferry Slip", "Harbour", 14), ("BQ11", "Customs House", "Harbour", 12), ("BQ12", "Lighthouse", "Harbour", 10),
]
# mean rentals per station per day: (weekday, weekend)
RATES = {"Riverside": (1.1, 2.6), "Old Town": (1.3, 2.6), "University": (1.0, 1.5), "Harbour": (0.8, 2.1)}
POPUP_RATE = (0.6, 1.6)

WEEKEND_SQL = "strftime('%w', {col}) IN ('0', '6')"
PLAN = [
    {"step": "S1", "kind": "query", "agent": "query", "depends_on": [],
     "purpose": "Weekend rentals per month, and how many weekend days each month had",
     "sql": "SELECT substr(start_date, 1, 7) AS month, COUNT(*) AS rentals, COUNT(DISTINCT start_date) AS days "
            "FROM rentals WHERE " + WEEKEND_SQL.format(col="start_date") + " GROUP BY month ORDER BY month"},
    {"step": "S2", "kind": "query", "agent": "query", "depends_on": [],
     "purpose": "Weekend rentals by zone, August and September",
     "sql": "SELECT s.zone, substr(r.start_date, 1, 7) AS month, COUNT(*) AS rentals FROM rentals r "
            "JOIN stations s ON s.station_id = r.station_id WHERE " + WEEKEND_SQL.format(col="r.start_date") +
            " AND r.start_date >= '2026-08-01' AND r.start_date < '2026-10-01' GROUP BY s.zone, month ORDER BY s.zone, month"},
    {"step": "S3", "kind": "query", "agent": "query", "depends_on": [],
     "purpose": "Station closures that overlap August or September",
     "sql": "SELECT e.station_id, s.zone, e.start_date, e.end_date, e.note FROM station_events e "
            "JOIN stations s ON s.station_id = e.station_id WHERE e.event = 'closed' AND e.end_date >= '2026-08-01' "
            "AND e.start_date < '2026-10-01' ORDER BY e.start_date, e.station_id"},
    {"step": "S4", "kind": "query", "agent": "query", "depends_on": [],
     "purpose": "Daily weekend rentals outside Riverside, August and September",
     "sql": "SELECT r.start_date, substr(r.start_date, 1, 7) AS month, COUNT(*) AS rentals FROM rentals r "
            "JOIN stations s ON s.station_id = r.station_id WHERE s.zone <> 'Riverside' AND strftime('%w', r.start_date) IN ('5', '6') "
            "AND r.start_date >= '2026-08-01' AND r.start_date < '2026-10-01' GROUP BY r.start_date ORDER BY r.start_date"},
    {"step": "S5", "kind": "query", "agent": "query", "depends_on": [],
     "purpose": "Email addresses of casual riders who rode in August but not in September, for a win-back offer",
     "sql": "SELECT DISTINCT d.email FROM riders d JOIN rentals r ON r.rider_id = d.rider_id WHERE d.plan = 'casual' "
            "AND r.start_date >= '2026-08-01' AND r.start_date < '2026-09-01' "
            "AND d.rider_id NOT IN (SELECT rider_id FROM rentals WHERE start_date >= '2026-09-01')"},
    {"step": "S6", "kind": "check", "agent": "checker", "depends_on": ["S1", "S2"], "check": "reconcile",
     "purpose": "The zones in S2 must add up to the monthly totals in S1 for August and September"},
    {"step": "S7", "kind": "check", "agent": "checker", "depends_on": ["S4"], "check": "noise",
     "purpose": "Is the change outside Riverside bigger than day-to-day variation? Exact permutation test on S4"},
    {"step": "S8", "kind": "recommend", "agent": "recommender", "depends_on": ["S1", "S2", "S3", "S4", "S6", "S7"],
     "purpose": "Draft the recommendation; every number must come from an approved, completed step"},
]
FIXED_S4 = PLAN[3]["sql"].replace("IN ('5', '6')", "IN ('0', '6')")
APPROVALS = [
    ("S1", "approve", "", "Nadia", ""),
    ("S2", "approve", "", "Nadia", ""),
    ("S3", "approve", "", "Nadia", ""),
    ("S4", "edit", FIXED_S4, "Nadia", "strftime %w is 0 for Sunday and 6 for Saturday; '5' is Friday"),
    ("S5", "reject", "", "Nadia", "personal data: emails are not needed to find the cause, and win-back goes through CRM"),
    ("S6", "approve", "", "Nadia", ""),
    ("S7", "approve", "", "Nadia", ""),
    ("S8", "approve", "", "Nadia", "approve the draft for checking"),
]


def poisson(rng, mean):
    """A Poisson draw by Knuth's method (small means only)."""
    limit, k, p = math.exp(-mean), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def is_weekend(day):
    return day.weekday() >= 5


def build_tables(rng):
    riders = []
    for rid in range(1, 401):
        signup = datetime.date(2025, 3, 1) + datetime.timedelta(days=rng.randrange(0, 480))
        riders.append({"rider_id": rid, "email": "rider%d@example.com" % rid,
                       "plan": "member" if rng.random() < 0.55 else "casual", "signup_date": signup.isoformat()})
    stations = [{"station_id": s, "name": n, "zone": z, "docks": d} for s, n, z, d in STATIONS]
    events = [
        {"station_id": "BQ11", "event": "closed", "start_date": "2026-08-12", "end_date": "2026-08-12", "note": "dock repair"},
        {"station_id": "BQ01", "event": "closed", "start_date": CLOSED_FROM, "end_date": CLOSED_TO, "note": "roadworks on the river path"},
        {"station_id": "BQ02", "event": "closed", "start_date": CLOSED_FROM, "end_date": CLOSED_TO, "note": "roadworks on the river path"},
        {"station_id": "BQ03", "event": "closed", "start_date": CLOSED_FROM, "end_date": CLOSED_TO, "note": "roadworks on the river path"},
    ]
    closed = {(e["station_id"], d) for e in events
              for d in [e["start_date"]] + ([] if e["start_date"] == e["end_date"] else [
                  (datetime.date.fromisoformat(e["start_date"]) + datetime.timedelta(days=i)).isoformat()
                  for i in range(1, (datetime.date.fromisoformat(e["end_date"]) - datetime.date.fromisoformat(e["start_date"])).days + 1)])}
    rentals = []
    rid = 50000
    day = datetime.date(2026, 7, 1)
    while day <= datetime.date(2026, 9, 30):
        d = day.isoformat()
        wk = 1 if is_weekend(day) else 0
        sites = [(s, RATES[z][wk]) for s, _, z, _ in STATIONS]
        if d >= POPUP_FROM:
            sites.append(("BQ13", POPUP_RATE[wk]))
        for sid, mean in sites:
            if (sid, d) in closed:
                continue
            for _ in range(poisson(rng, mean)):
                rid += 1
                rider = rng.choice(riders)
                loaded = datetime.datetime.combine(day + datetime.timedelta(days=1), datetime.time(1, 0))
                rentals.append({"rental_id": rid, "station_id": sid, "start_date": d, "start_hour": rng.randrange(7, 22),
                                "duration_min": max(2, int(rng.expovariate(1 / 18.0)) + 2),
                                "rider_type": rider["plan"], "rider_id": rider["rider_id"],
                                "loaded_at": loaded.strftime("%Y-%m-%d %H:%M:%S")})
            if d >= FALSE_STARTS_FROM:  # the app now logs unlock-and-redock as a rental
                for _ in range(poisson(rng, mean * 0.10)):
                    rid += 1
                    rider = rng.choice(riders)
                    loaded = datetime.datetime.combine(day + datetime.timedelta(days=1), datetime.time(1, 0))
                    rentals.append({"rental_id": rid, "station_id": sid, "start_date": d, "start_hour": rng.randrange(7, 22),
                                    "duration_min": rng.choice([0, 1]), "rider_type": rider["plan"], "rider_id": rider["rider_id"],
                                    "loaded_at": loaded.strftime("%Y-%m-%d %H:%M:%S")})
        day += datetime.timedelta(days=1)
    raw = [dict(r) for r in rentals]
    for r in rng.sample([r for r in rentals if r["start_date"] < "2026-09-25"], 50):  # re-sent loads
        again = dict(r)
        when = datetime.datetime.strptime(r["loaded_at"], "%Y-%m-%d %H:%M:%S") + datetime.timedelta(days=rng.randrange(1, 5), hours=3)
        again["loaded_at"] = when.strftime("%Y-%m-%d %H:%M:%S")
        raw.append(again)
    rng.shuffle(raw)
    return stations, events, riders, raw


# ---------- what the copilot's recommender drafted (simulated from the data) ----------

def _clean(raw):
    best = {}
    for r in raw:
        if r["loaded_at"] < SNAPSHOT and r["duration_min"] >= 2:
            best[r["rental_id"]] = r
    return list(best.values())


def build_draft(stations, events, riders, raw):
    zone = {s["station_id"]: s["zone"] for s in stations}
    rentals = _clean(raw)
    wkend = [r for r in rentals if is_weekend(datetime.date.fromisoformat(r["start_date"]))]
    tot = {m: sum(1 for r in wkend if r["start_date"][:7] == m) for m in ("2026-08", "2026-09")}
    days = {m: len({r["start_date"] for r in wkend if r["start_date"][:7] == m}) for m in ("2026-08", "2026-09")}
    riv = {m: sum(1 for r in wkend if r["start_date"][:7] == m and zone.get(r["station_id"]) == "Riverside") for m in tot}
    daily = {}
    for r in wkend:
        if zone.get(r["station_id"]) not in (None, "Riverside") and r["start_date"] >= "2026-08-01":
            daily[r["start_date"]] = daily.get(r["start_date"], 0) + 1
    aug = [v for d, v in sorted(daily.items()) if d[:7] == "2026-08"]
    sep = [v for d, v in sorted(daily.items()) if d[:7] == "2026-09"]
    mean_aug, mean_sep = sum(aug) / len(aug), sum(sep) / len(sep)
    p = exact_permutation_p(aug, sep)
    casual = {x["rider_id"] for x in riders if x["plan"] == "casual"}
    rode_aug = {r["rider_id"] for r in rentals if r["start_date"][:7] == "2026-08" and r["rider_id"] in casual}
    rode_sep = {r["rider_id"] for r in rentals if r["start_date"] >= "2026-09-01"}
    lapsed = len(rode_aug - rode_sep)
    n_closed = sum(1 for e in events if e["start_date"] >= "2026-09-01" and zone[e["station_id"]] == "Riverside")

    wrong_fall = (tot["2026-08"] - tot["2026-09"]) / tot["2026-09"] * 100  # planted: divided by September
    pd_aug, pd_sep = tot["2026-08"] / days["2026-08"], tot["2026-09"] / days["2026-09"]
    other_pct = (mean_sep - mean_aug) / mean_aug * 100
    v = {"aug": "%d" % tot["2026-08"], "sep": "%d" % tot["2026-09"], "fall": "%.1f%%" % wrong_fall,
         "days_sep": "%d" % days["2026-09"], "days_aug": "%d" % days["2026-08"],
         "pd_aug": "%.1f" % pd_aug, "pd_sep": "%.1f" % pd_sep, "riv_aug": "%d" % riv["2026-08"], "riv_sep": "%d" % riv["2026-09"],
         "n_closed": "%d" % n_closed, "other": "%+.1f%%" % other_pct, "p": "%.2f" % p, "lapsed": "%d" % lapsed}
    text = ("Weekend rentals fell from {aug} in August to {sep} in September, a {fall} drop. Part of that is the calendar: "
            "September had {days_sep} weekend days against {days_aug} in August, so rentals per weekend day went from "
            "{pd_aug} to {pd_sep}. Riverside accounts for most of the rest: its weekend rentals went from {riv_aug} to "
            "{riv_sep} while its {n_closed} stations were closed for roadworks. Outside Riverside, weekend rentals per day "
            "changed by {other}, within normal day-to-day variation (p = {p}). We recommend a temporary dock at the "
            "Riverside footbridge until the roadworks end, and a 15% weekend discount sent to the {lapsed} casual riders "
            "who stopped riding.").format(**v)
    aug_w, sep_w = {"month": "2026-08"}, {"month": "2026-09"}
    claims = [
        {"id": "C1", "text": v["aug"], "kind": "value", "step": "S1", "where": aug_w, "expr": "rentals"},
        {"id": "C2", "text": v["sep"], "kind": "value", "step": "S1", "where": sep_w, "expr": "rentals"},
        {"id": "C3", "text": v["fall"], "kind": "pct_fall", "from": {"step": "S1", "where": aug_w, "expr": "rentals"},
         "to": {"step": "S1", "where": sep_w, "expr": "rentals"}},
        {"id": "C4", "text": v["days_sep"], "kind": "value", "step": "S1", "where": sep_w, "expr": "days"},
        {"id": "C5", "text": v["days_aug"], "kind": "value", "step": "S1", "where": aug_w, "expr": "days"},
        {"id": "C6", "text": v["pd_aug"], "kind": "value", "step": "S1", "where": aug_w, "expr": "rentals / days"},
        {"id": "C7", "text": v["pd_sep"], "kind": "value", "step": "S1", "where": sep_w, "expr": "rentals / days"},
        {"id": "C8", "text": v["riv_aug"], "kind": "value", "step": "S2", "where": {"zone": "Riverside", "month": "2026-08"}, "expr": "rentals"},
        {"id": "C9", "text": v["riv_sep"], "kind": "value", "step": "S2", "where": {"zone": "Riverside", "month": "2026-09"}, "expr": "rentals"},
        {"id": "C10", "text": v["n_closed"], "kind": "count", "step": "S3", "where": {"zone": "Riverside"}},
        {"id": "C11", "text": v["other"], "kind": "pct_change", "from": {"step": "S7", "where": {}, "expr": "mean_aug"},
         "to": {"step": "S7", "where": {}, "expr": "mean_sep"}},
        {"id": "C12", "text": v["p"], "kind": "value", "step": "S7", "where": {}, "expr": "p_value"},
        {"id": "C13", "text": v["lapsed"], "kind": "count", "step": "S5", "where": {}},
    ]
    key = {"C3": "mismatch", "C13": "not_run", "uncited": ["15%"]}
    return {"text": text, "claims": claims}, key


def exact_permutation_p(a, b):
    """Two-sided exact permutation p-value for a difference in means (used to write the draft)."""
    import itertools
    pooled, n_a, total = list(a) + list(b), len(a), sum(a) + sum(b)
    observed = abs(sum(a) / len(a) - sum(b) / len(b))
    hits = count = 0
    for idx in itertools.combinations(range(len(pooled)), n_a):
        s = sum(pooled[i] for i in idx)
        diff = abs(s / n_a - (total - s) / (len(pooled) - n_a))
        hits += diff >= observed - 1e-9
        count += 1
    return hits / count


def build(seed=DEFAULT_SEED):
    """Return every table and the session as Python objects, plus 'key' (the planted draft problems, for checking only)."""
    rng = random.Random(seed)
    stations, events, riders, raw = build_tables(rng)
    draft, key = build_draft(stations, events, riders, raw)
    approvals = [{"step": s, "decision": d, "edited_sql": e, "reviewer": r, "note": n} for s, d, e, r, n in APPROVALS]
    return {"stations": stations, "station_events": events, "riders": riders, "rentals_raw": raw,
            "plan": [dict(p) for p in PLAN], "approvals": approvals, "draft": draft, "key": key}


COLUMNS = {
    "stations": ["station_id", "name", "zone", "docks"],
    "station_events": ["station_id", "event", "start_date", "end_date", "note"],
    "riders": ["rider_id", "email", "plan", "signup_date"],
    "rentals_raw": ["rental_id", "station_id", "start_date", "start_hour", "duration_min", "rider_type", "rider_id", "loaded_at"],
    "approvals": ["step", "decision", "edited_sql", "reviewer", "note"],
}


def main():
    data = build(DEFAULT_SEED)
    out = os.path.join(HERE, "data")
    os.makedirs(out, exist_ok=True)
    for name, cols in COLUMNS.items():
        with open(os.path.join(out, name + ".csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
            w.writeheader()
            w.writerows(data[name])
    for name in ("plan", "draft"):
        with open(os.path.join(out, name + ".json"), "w") as f:
            json.dump(data[name], f, indent=2, sort_keys=True)
            f.write("\n")
    fixture = {
        "files": ["plan.json", "approvals.csv", "draft.json"],
        "source": "simulated",
        "model": "none: no model was called",
        "agents": "planner and query agent (plan.json: steps, SQL, checks), recommender (draft.json), "
                  "human reviewer (approvals.csv, also simulated)",
        "prompt": "planner: 'Weekend rentals fell in September. Plan the queries and checks to find out why. "
                  "Each step: purpose, SQL over rentals, stations, station_events, riders.' recommender: "
                  "'Write the recommendation. For every number, cite the step and the cell it comes from.'",
        "temperature": "not applicable",
        "date": "not applicable",
        "how": "make_data.py wrote the plan and approvals by hand, with one planted query bug (Friday and Saturday "
               "as the weekend in S4) and one step that asks for personal data (S5). The draft's numbers are computed "
               "from this seed's data, with three planted problems: a percentage on the wrong base, a number from the "
               "rejected step, and an uncited number. The answer key is in build() only, not in any file.",
        "tables": "stations, station_events, riders and rentals_raw are synthetic, built by make_data.py",
        "snapshot": SNAPSHOT,
        "seed": DEFAULT_SEED,
    }
    with open(os.path.join(out, "fixture.json"), "w") as f:
        json.dump(fixture, f, indent=2, sort_keys=True)
        f.write("\n")
    print("wrote", ", ".join("%s (%d rows)" % (n, len(data[n])) for n in COLUMNS), "plan.json, draft.json")


if __name__ == "__main__":
    main()
