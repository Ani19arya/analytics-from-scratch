"""Capstone 10-02: Chordwhistle retention and cohorts. Worked solution.

Read solution/WRITEUP.md for the reasoning and the one-page write-up. Run this
file from the capstone folder to print the numbers:

    python3 solution/solution.py
"""
import csv
import math
import os

LAST_COMPLETE_MONTH = "2026-09"


def load(folder):
    """Read users.csv and activity.csv from `folder`: {"users", "activity"}, rows as dicts of text."""
    out = {}
    for name in ("users", "activity"):
        with open(os.path.join(folder, name + ".csv"), newline="") as f:
            out[name] = list(csv.DictReader(f))
    return out


def months_between(start, end):
    """Whole calendar months from 'YYYY-MM' start to end: ('2026-01', '2026-03') -> 2."""
    return (int(end[:4]) - int(start[:4])) * 12 + int(end[5:7]) - int(start[5:7])


def clean_users(raw_users):
    """{user_id: {"signup_month", "platform", "source"}}: one entry per user, staff accounts left out."""
    out = {}
    for u in raw_users:
        if u["account_type"] != "customer":
            continue
        out[u["user_id"]] = {"signup_month": u["signup_date"][:7], "platform": u["platform"], "source": u["source"]}
    return dict(sorted(out.items()))


def active_months(raw_activity, users, last_month=LAST_COMPLETE_MONTH):
    """{user_id: set of 'YYYY-MM'} in which the user completed at least one lesson.
    Only users in `users`, only months from their sign-up month up to `last_month`."""
    out = {uid: set() for uid in users}
    for r in raw_activity:
        uid, month = r["user_id"], r["activity_month"]
        if uid not in users or month > last_month or month < users[uid]["signup_month"]:
            continue
        if int(r["lessons_completed"]) >= 1:
            out[uid].add(month)
    return out


def retention_matrix(users, active, last_month=LAST_COMPLETE_MONTH):
    """{cohort month: {"size", "active": [count at month 0, 1, ...], "rates": [...]}}.
    A cohort's lists stop at last_month: later months have not been observed (right-censored)."""
    cohorts = {}
    for uid, u in users.items():
        if u["signup_month"] <= last_month:
            cohorts.setdefault(u["signup_month"], []).append(uid)
    out = {}
    for c in sorted(cohorts):
        ids = cohorts[c]
        horizon = months_between(c, last_month)
        counts = [0] * (horizon + 1)
        for uid in ids:
            for m in active.get(uid, ()):
                counts[months_between(c, m)] += 1
        out[c] = {"size": len(ids), "active": counts, "rates": [n / len(ids) for n in counts]}
    return out


def pooled_curve(matrix):
    """Retention at month k pooled over every cohort observed at k: sum of active / sum of sizes."""
    longest = max((len(row["active"]) for row in matrix.values()), default=0)
    curve = []
    for k in range(longest):
        rows = [row for row in matrix.values() if len(row["active"]) > k]
        curve.append(sum(r["active"][k] for r in rows) / sum(r["size"] for r in rows))
    return curve


def shortfall(matrix, k=1):
    """[(cohort, users_lost), ...], biggest first (ties by cohort). users_lost = size x (pooled
    month-k retention of all OTHER cohorts observed at k - this cohort's month-k retention)."""
    seen = {c: row for c, row in matrix.items() if len(row["active"]) > k}
    out = []
    for c, row in seen.items():
        others = [r for o, r in seen.items() if o != c]
        if not others:
            continue
        base = sum(r["active"][k] for r in others) / sum(r["size"] for r in others)
        out.append((c, row["size"] * (base - row["rates"][k])))
    return sorted(out, key=lambda t: (-t[1], t[0]))


def two_proportion_z(x1, n1, x2, n2):
    """Two-sided test of p1 = p2 with the pooled standard error.
    Returns {"diff", "z", "p_value"} with diff = x1/n1 - x2/n2; None if a group is empty or SE is 0."""
    if n1 == 0 or n2 == 0:
        return None
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return None
    diff = x1 / n1 - x2 / n2
    z = diff / se
    return {"diff": diff, "z": z, "p_value": math.erfc(abs(z) / math.sqrt(2))}


def retention_by_segment(users, active, cohort, k, field):
    """{segment value: {"size", "active", "rate"}} for one cohort at month k, split by `field`
    ("source" or "platform")."""
    target = month_plus(cohort, k)
    out = {}
    for uid, u in users.items():
        if u["signup_month"] != cohort:
            continue
        seg = out.setdefault(u[field], {"size": 0, "active": 0})
        seg["size"] += 1
        seg["active"] += target in active.get(uid, ())
    for seg in out.values():
        seg["rate"] = seg["active"] / seg["size"]
    return dict(sorted(out.items()))


def month_plus(month, k):
    y, m = int(month[:4]), int(month[5:7]) + k
    y, m = y + (m - 1) // 12, (m - 1) % 12 + 1
    return "%d-%02d" % (y, m)


# ---- the deliverable chart ------------------------------------------------

def curve_by_source(users, active, last_month=LAST_COMPLETE_MONTH, max_k=5):
    """{source: [pooled retention at month 0..max_k]} over the cohorts observed at each month."""
    out = {}
    for source in sorted({u["source"] for u in users.values()}):
        subset = {uid: u for uid, u in users.items() if u["source"] == source}
        out[source] = pooled_curve(retention_matrix(subset, active, last_month))[:max_k + 1]
    return out


def line_chart_svg(series, title, width=560, height=280):
    """A plain SVG line chart: {name: [values 0..1]}, x = month since sign-up, y from 0% to 100%."""
    colors = ["#3b6ea5", "#c0504d", "#4f9a55", "#8064a2"]
    left, top, bottom, right = 60, 40, height - 40, width - 130
    n = max(len(v) for v in series.values())
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" font-family="sans-serif" font-size="11">'
             % (width, height), '<rect width="100%" height="100%" fill="white"/>',
             '<text x="%d" y="22" font-size="13">%s</text>' % (left, title)]
    for i in range(6):
        y = bottom - (bottom - top) * i / 5
        parts.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#ddd"/>' % (left, right, y, y))
        parts.append('<text x="%d" y="%.1f" text-anchor="end">%d%%</text>' % (left - 6, y + 4, 20 * i))
    for k in range(n):
        x = left + (right - left) * k / (n - 1)
        parts.append('<text x="%.1f" y="%d" text-anchor="middle">%d</text>' % (x, bottom + 16, k))
    parts.append('<text x="%d" y="%d" text-anchor="middle">months since sign-up</text>' % ((left + right) // 2, bottom + 32))
    for (name, values), color in zip(series.items(), colors):
        pts = " ".join("%.1f,%.1f" % (left + (right - left) * k / (n - 1), bottom - (bottom - top) * v)
                       for k, v in enumerate(values))
        parts.append('<polyline fill="none" stroke="%s" stroke-width="2" points="%s"/>' % (color, pts))
        y = bottom - (bottom - top) * values[-1]
        parts.append('<text x="%d" y="%.1f" fill="%s">%s</text>' % (right + 8, y + 4, color, name))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw = load(os.path.join(here, "data"))
    users = clean_users(raw["users"])
    active = active_months(raw["activity"], users)
    matrix = retention_matrix(users, active)
    print("users %d (raw rows %d)" % (len(users), len(raw["users"])))
    for c, row in matrix.items():
        print(c, "%4d" % row["size"], " ".join("%3.0f%%" % (100 * r) for r in row["rates"]))
    print("pooled", " ".join("%.1f%%" % (100 * r) for r in pooled_curve(matrix)))
    ranked = shortfall(matrix, 1)
    print("month-1 shortfall", [(c, round(x, 1)) for c, x in ranked])
    top = ranked[0][0]
    row = matrix[top]
    rest = [r for c, r in matrix.items() if c != top and len(r["active"]) > 1]
    t = two_proportion_z(row["active"][1], row["size"], sum(r["active"][1] for r in rest), sum(r["size"] for r in rest))
    print("%s vs other cohorts at month 1: diff %.3f z %.2f p %.2g" % (top, t["diff"], t["z"], t["p_value"]))
    for field in ("source", "platform"):
        print(top, field, {s: (v["active"], v["size"], round(v["rate"], 3))
                           for s, v in retention_by_segment(users, active, top, 1, field).items()})
    curves = curve_by_source(users, active)
    for source, values in curves.items():
        print("curve", source, " ".join("%.0f%%" % (100 * v) for v in values))
    with open(os.path.join(here, "solution", "retention_by_source.svg"), "w") as f:
        f.write(line_chart_svg(curves, "Chordwhistle retention by source, all cohorts pooled (synthetic data)"))


if __name__ == "__main__":
    main()
