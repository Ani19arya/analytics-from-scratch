"""Capstone 10-06: the Parcelwick weekly business review that builds, tests and
sends itself. Worked solution.

Read DELIVERABLES.md for what each function must return, and solution/WRITEUP.md
for the reasoning. Sending means writing an .eml file to an outbox folder:
nothing here touches the network.

    python3 solution/solution.py
        rebuilds solution/sample_outbox/ by running the weeks of 12 and 19
        October 2026 in order (the second email shows a restatement)
    python3 solution/solution.py --week 2026-10-19 --outbox outbox
        runs one week into ./outbox, as a scheduler would
"""
import csv
import datetime as dt
import email.utils
import glob
import json
import os
import re
import shutil
import sys
from email.message import EmailMessage

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTCOMES = {"D": "delivered", "F": "failed", "R": "returned",
            "delivered": "delivered", "failed": "failed", "returned": "returned"}


# ---- given ------------------------------------------------------------------------

def load_config(path=os.path.join(HERE, "report_config.json")):
    with open(path) as f:
        return json.load(f)


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def add_days(date_text, n):
    return (dt.date.fromisoformat(date_text) + dt.timedelta(days=n)).isoformat()


def week_of(date_text):
    """The Monday (ISO week start) of the week a 'YYYY-MM-DD' date falls in."""
    d = dt.date.fromisoformat(date_text)
    return (d - dt.timedelta(days=d.weekday())).isoformat()


def load_state(outbox):
    path = os.path.join(outbox, "state.json")
    if not os.path.exists(path):
        return {"sent": {}}
    with open(path) as f:
        return json.load(f)


def save_state(outbox, state):
    os.makedirs(outbox, exist_ok=True)
    with open(os.path.join(outbox, "state.json"), "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def write_email(path, sender, to, subject, body, when, attachments=()):
    """'Send' an email by writing it to path as an .eml file. when: a datetime for the Date
    header. attachments: (filename, text, subtype) tuples, for example ("chart.svg", svg, "svg+xml").
    The output is byte-for-byte the same for the same inputs."""
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    msg["Subject"] = subject
    msg["Date"] = email.utils.format_datetime(when)
    msg.set_content(body)
    for name, text, subtype in attachments:
        msg.add_attachment(text.encode("utf-8"), maintype="image" if subtype.startswith("svg") else "text",
                           subtype=subtype, filename=name)
    if attachments:
        msg.set_boundary("wbr-boundary-" + re.sub(r"[^0-9A-Za-z]", "", subject)[:40])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(bytes(msg))
    return path


# ---- yours ------------------------------------------------------------------------

def read_drops(drop_dir, up_to):
    """Every row of every drop file parcels_YYYY-MM-DD*.csv in drop_dir whose drop date
    (the date in the name) is on or before up_to, oldest drop first, in file order.
    Each row is the CSV dict plus "drop" (the drop date) and "file" (the file name)."""
    rows = []
    for path in sorted(glob.glob(os.path.join(drop_dir, "parcels_*.csv"))):
        name = os.path.basename(path)
        drop = name[len("parcels_"):len("parcels_") + 10]
        if drop <= up_to:
            for r in read_csv(path):
                r = dict(r)
                r["drop"], r["file"] = drop, name
                rows.append(r)
    rows.sort(key=lambda r: r["drop"])
    return rows


def normalise_outcome(value):
    """'D', 'F', 'R' (old app) or 'delivered', 'failed', 'returned' (new app), any case and
    surrounding spaces, to 'delivered', 'failed' or 'returned'. Anything else: None."""
    return OUTCOMES.get((value or "").strip()) or OUTCOMES.get((value or "").strip().lower())


def clean_parcels(rows):
    """{parcel_id: parcel} with each parcel's latest outcome: the row with the latest
    outcome_date, then the latest drop, then the later row. Rows whose outcome does not
    normalise are skipped. parcel: site_id, promised_date, outcome (normalised),
    outcome_date, fee_gbp (float)."""
    out = {}
    for r in rows:
        outcome = normalise_outcome(r.get("outcome"))
        if outcome is None:
            continue
        key = (r["outcome_date"], r["drop"])
        cur = out.get(r["parcel_id"])
        if cur is None or key >= cur["_key"]:
            out[r["parcel_id"]] = {"site_id": r["site_id"], "promised_date": r["promised_date"], "outcome": outcome,
                                   "outcome_date": r["outcome_date"], "fee_gbp": float(r["fee_gbp"]), "_key": key}
    for p in out.values():
        del p["_key"]
    return out


def weekly_kpis(parcels, week_start):
    """KPIs for the week starting week_start (Monday to Sunday). A parcel belongs to the
    week of its latest outcome_date (when it was resolved, as far as we know today):
    parcels, delivered, on_time (delivered on or before promised_date), on_time_pct
    (100 x on_time / parcels, 2 decimals, None with no parcels), failed, returned,
    revenue_gbp (fees of delivered parcels, 2 decimals), and sites: {site_id: {"parcels",
    "on_time_pct", "revenue_gbp"}} for sites with parcels that week."""
    end = add_days(week_start, 6)
    mine = [p for p in parcels.values() if week_start <= p["outcome_date"] <= end]

    def summary(ps):
        on_time = sum(1 for p in ps if p["outcome"] == "delivered" and p["outcome_date"] <= p["promised_date"])
        return {"parcels": len(ps),
                "delivered": sum(1 for p in ps if p["outcome"] == "delivered"),
                "on_time": on_time,
                "on_time_pct": round(100.0 * on_time / len(ps), 2) if ps else None,
                "failed": sum(1 for p in ps if p["outcome"] == "failed"),
                "returned": sum(1 for p in ps if p["outcome"] == "returned"),
                "revenue_gbp": round(sum(p["fee_gbp"] for p in ps if p["outcome"] == "delivered"), 2)}

    out = dict(summary(mine), week=week_start)
    out["sites"] = {}
    for sid in sorted({p["site_id"] for p in mine}):
        s = summary([p for p in mine if p["site_id"] == sid])
        out["sites"][sid] = {"parcels": s["parcels"], "on_time_pct": s["on_time_pct"], "revenue_gbp": s["revenue_gbp"]}
    return out


def validate(rows, sites, week_start, config):
    """Checks to run before the report is built. Returns a list of issues, each
    {"level": "error" or "warn", "check": name, "detail": one sentence}. Errors block sending:
      schema       a required column (config["required_columns"]) is missing from any drop file
                   (one issue per file and column; when there is one, return straight away);
      outcome      rows whose outcome does not normalise (one issue with the count);
      empty        no parcels in the week;
      volume       parcels in the week below config["min_volume_ratio"] x the mean of the
                   previous 4 weeks (only when all 4 weeks have parcels).
    Warnings go into the report:
      site_silent  a site in sites with no parcels in the week but parcels in each of the
                   previous config["outage_lookback_weeks"] weeks (one issue per site);
      unknown_site rows whose site_id is not in sites (one issue with the count)."""
    issues = []
    seen = {}
    for r in rows:
        seen.setdefault(r["file"], set(k for k in r if k not in ("drop", "file") and r[k] is not None))
    for name in sorted(seen):
        for col in config["required_columns"]:
            if col not in seen[name]:
                issues.append({"level": "error", "check": "schema", "detail": "%s has no column %s" % (name, col)})
    if issues:
        return issues
    bad = sum(1 for r in rows if normalise_outcome(r["outcome"]) is None)
    if bad:
        issues.append({"level": "error", "check": "outcome",
                       "detail": "%d rows have an outcome that is not a known code or word" % bad})
    parcels = clean_parcels(rows)
    k = weekly_kpis(parcels, week_start)
    if k["parcels"] == 0:
        issues.append({"level": "error", "check": "empty", "detail": "no parcels in the week of %s" % week_start})
    history = [weekly_kpis(parcels, add_days(week_start, -7 * i)) for i in range(1, 5)]
    if k["parcels"] and all(h["parcels"] for h in history):
        mean = sum(h["parcels"] for h in history) / 4.0
        if k["parcels"] < config["min_volume_ratio"] * mean:
            issues.append({"level": "error", "check": "volume",
                           "detail": "%d parcels, under %.0f%% of the 4-week mean of %.1f"
                                     % (k["parcels"], 100 * config["min_volume_ratio"], mean)})
    site_ids = [s["site_id"] for s in sites]
    lookback = [weekly_kpis(parcels, add_days(week_start, -7 * i)) for i in range(1, config["outage_lookback_weeks"] + 1)]
    for sid in site_ids:
        if sid not in k["sites"] and all(sid in h["sites"] for h in lookback):
            issues.append({"level": "warn", "check": "site_silent",
                           "detail": "site %s sent no parcels for the week of %s; it did in each of the %d weeks before"
                                     % (sid, week_start, len(lookback))})
    unknown = sum(1 for r in rows if r["site_id"] not in site_ids)
    if unknown:
        issues.append({"level": "warn", "check": "unknown_site", "detail": "%d rows have a site_id not in sites.csv" % unknown})
    return issues


def fmt(v, kind):
    if v is None:
        return "n/a"
    return "%.2f%%" % v if kind == "pct" else ("GBP %.2f" % v if kind == "gbp" else str(v))


def change(now, before, kind):
    if now is None or before is None:
        return "n/a"
    if kind == "pct":
        return "%+.2f pts" % (now - before)
    if not before:
        return "n/a"
    return "%+.1f%%" % (100.0 * (now - before) / before)


SUMMARY = [("parcels", "count"), ("delivered", "count"), ("on_time_pct", "pct"), ("failed", "count"),
           ("returned", "count"), ("revenue_gbp", "gbp")]


def render_report(kpis, previous, previous_as_sent, issues, site_names=None, site_trend=None):
    """The email body, plain text (Markdown). It starts with the title line and a summary
    block of exactly these lines, in this order, so a machine can read it:
        parcels: <int>
        delivered: <int>
        on_time_pct: <2 decimals, or n/a>
        failed: <int>
        returned: <int>
        revenue_gbp: <2 decimals>
    Then a comparison with `previous` (last week as known now), a table by site, a
    'Restated' note when previous_as_sent (last week as it was sent) differs from previous
    on parcels or on_time_pct, a 'Data warnings' section listing every warn issue, and a
    footer saying the data is synthetic. Optional: site_names {site_id: name} for the site
    table, and site_trend {site_id: [(week, on_time_pct), ...]} for a table of on-time by
    site over recent weeks (the test does not check either)."""
    names = site_names or {}
    lines = ["# Parcelwick weekly business review, week of %s" % kpis["week"], ""]
    for key, _ in SUMMARY:
        v = kpis[key]
        lines.append("%s: %s" % (key, "n/a" if v is None else ("%.2f" % v if isinstance(v, float) else v)))
    lines += ["", "## Against last week (week of %s, as known today)" % previous["week"], "",
              "| KPI | This week | Last week | Change |", "|---|---|---|---|"]
    for key, kind in SUMMARY:
        lines.append("| %s | %s | %s | %s |" % (key, fmt(kpis[key], kind), fmt(previous[key], kind),
                                                change(kpis[key], previous[key], kind)))
    lines += ["", "Rates change in percentage points (pts); counts and revenue in percent.", "",
              "## By site", "", "| Site | Parcels | On time | Revenue |", "|---|---|---|---|"]
    for sid, s in sorted(kpis["sites"].items()):
        label = "%s %s" % (sid, names.get(sid, "")) if names.get(sid) else sid
        lines.append("| %s | %d | %s | %s |" % (label.strip(), s["parcels"], fmt(s["on_time_pct"], "pct"),
                                                 fmt(s["revenue_gbp"], "gbp")))
    if site_trend:
        weeks = [w for w, _ in next(iter(site_trend.values()))]
        lines += ["", "## On time by site, last %d weeks" % len(weeks), "",
                  "| Site | " + " | ".join(w[5:] for w in weeks) + " |", "|---|" + "---|" * len(weeks)]
        for sid, pts in sorted(site_trend.items()):
            label = ("%s %s" % (sid, names.get(sid, ""))).strip()
            lines.append("| %s | " % label + " | ".join("n/a" if v is None else "%.1f" % v for _, v in pts) + " |")
    if previous_as_sent and (previous_as_sent["parcels"] != previous["parcels"]
                             or previous_as_sent["on_time_pct"] != previous["on_time_pct"]):
        lines += ["", "## Restated",
                  "",
                  "Last week's email said %s parcels and %s on time. With late rows that arrived since, it is "
                  "%s parcels and %s on time. The table above uses the restated numbers."
                  % (previous_as_sent["parcels"], fmt(previous_as_sent["on_time_pct"], "pct"),
                     previous["parcels"], fmt(previous["on_time_pct"], "pct"))]
    warns = [i for i in issues if i["level"] == "warn"]
    if warns:
        lines += ["", "## Data warnings", ""] + ["- %s: %s" % (i["check"], i["detail"]) for i in warns]
    lines += ["", "A parcel counts in the week of its latest outcome. On time = delivered on or before the "
                  "promised date. A week can still change when late rows arrive.",
              "Synthetic data. Built, checked and sent by the weekly pipeline; reply to analytics with questions."]
    return "\n".join(lines) + "\n"


def trend_svg(points):
    """A small bar chart of on-time % by week, axis from 0 to 100."""
    w, h, x0, y0, ph = 420, 180, 40, 150, 120
    bw = (w - x0 - 10) / float(max(1, len(points)))
    p = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" font-family="sans-serif" font-size="9">' % (w, h),
         '<rect width="100%" height="100%" fill="#ffffff"/>',
         '<text x="%d" y="14" font-size="11" fill="#222">On time, %% of parcels, by week (synthetic data)</text>' % x0]
    for v in (0, 50, 100):
        y = y0 - ph * v / 100.0
        p.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#ddd"/>' % (x0, w - 10, y, y))
        p.append('<text x="%d" y="%.1f" text-anchor="end" fill="#666">%d</text>' % (x0 - 4, y + 3, v))
    for i, (week, v) in enumerate(points):
        bh = ph * (v or 0) / 100.0
        p.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#3182bd"/>' % (x0 + i * bw + 2, y0 - bh, bw - 4, bh))
        p.append('<text x="%.1f" y="%d" text-anchor="middle" fill="#666">%s</text>' % (x0 + i * bw + bw / 2, y0 + 12, week[5:]))
    p.append("</svg>")
    return "\n".join(p) + "\n"


def run(data_dir, week_start, outbox, config):
    """The whole pipeline for one week. The week's drop is the Monday after it
    (week_start + 7 days); read every drop up to and including it.
      skipped  the week is already in the outbox state: write nothing, send nothing;
      blocked  validate found an error: write outbox/alerts/<week>_blocked.eml to
               config["alert_to"] listing every error, and do not touch the state;
      sent     write outbox/<week>_wbr.eml to config["to"] with subject
               "Parcelwick WBR, week of <week>: on time <on_time_pct, 1 decimal>%",
               and record the week's summary numbers in the state.
    Returns {"status", "path" (the file written, None when skipped), "issues"}."""
    state = load_state(outbox)
    if week_start in state["sent"]:
        return {"status": "skipped", "path": None, "issues": []}
    drop = add_days(week_start, 7)
    when = dt.datetime.combine(dt.date.fromisoformat(drop), dt.time(7, 0), tzinfo=dt.timezone.utc)
    rows = read_drops(os.path.join(data_dir, "drops"), drop)
    sites = read_csv(os.path.join(data_dir, "sites.csv"))
    issues = validate(rows, sites, week_start, config)
    errors = [i for i in issues if i["level"] == "error"]
    if errors:
        body = "The weekly business review for the week of %s was NOT sent. Fix these and run again:\n\n" % week_start
        body += "".join("- %s: %s\n" % (i["check"], i["detail"]) for i in errors)
        path = write_email(os.path.join(outbox, "alerts", "%s_blocked.eml" % week_start), config["sender"],
                           config["alert_to"], "Parcelwick WBR BLOCKED, week of %s: %d error(s)" % (week_start, len(errors)),
                           body, when)
        return {"status": "blocked", "path": path, "issues": issues}
    parcels = clean_parcels(rows)
    kpis = weekly_kpis(parcels, week_start)
    previous = weekly_kpis(parcels, add_days(week_start, -7))
    sent_prev = state["sent"].get(previous["week"], {}).get("kpis")
    names = {s["site_id"]: s["site_name"] for s in sites}
    weeks = [add_days(week_start, -7 * i) for i in range(3, -1, -1)]
    by_week = {w: weekly_kpis(parcels, w)["sites"] for w in weeks}
    trend = {sid: [(w, by_week[w].get(sid, {}).get("on_time_pct")) for w in weeks] for sid in sorted(names)}
    body = render_report(kpis, previous, sent_prev, issues, names, trend)
    chart = trend_svg([(add_days(week_start, -7 * i), weekly_kpis(parcels, add_days(week_start, -7 * i))["on_time_pct"])
                       for i in range(7, -1, -1)])
    subject = "Parcelwick WBR, week of %s: on time %s" % (
        week_start, "n/a" if kpis["on_time_pct"] is None else "%.1f%%" % kpis["on_time_pct"])
    path = write_email(os.path.join(outbox, "%s_wbr.eml" % week_start), config["sender"], config["to"], subject, body,
                       when, [("on_time_8_weeks.svg", chart, "svg+xml")])
    state["sent"][week_start] = {"file": os.path.basename(path), "kpis": {k: kpis[k] for k, _ in SUMMARY}}
    save_state(outbox, state)
    return {"status": "sent", "path": path, "issues": issues}


def main(argv):
    config = load_config()
    data = os.path.join(HERE, "data")
    if "--week" in argv:
        week = argv[argv.index("--week") + 1]
        outbox = argv[argv.index("--outbox") + 1] if "--outbox" in argv else "outbox"
        print(run(data, week, outbox, config))
        return
    sample = os.path.join(HERE, "solution", "sample_outbox")
    if os.path.isdir(sample):
        shutil.rmtree(sample)
    for week in ("2026-10-12", "2026-10-19", "2026-10-19"):
        r = run(data, week, sample, config)
        print(week, r["status"], os.path.relpath(r["path"], HERE) if r["path"] else "", [i["check"] for i in r["issues"]])


if __name__ == "__main__":
    main(sys.argv[1:])
