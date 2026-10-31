"""Capstone 10-03: Brambletoe marketing attribution and budget. Worked solution.

Read solution/WRITEUP.md for the reasoning and the one-page write-up. Run this
file from the capstone folder to print the numbers:

    python3 solution/solution.py
"""
import csv
import datetime
import math
import os

Q_START, Q_END = "2026-06-29", "2026-09-27"
TEST_START, TEST_END = "2026-08-03", "2026-08-30"
FEE_CHANGE_WEEK = "2026-08-17"
FEE = 0.15
PAID = ("paid_search", "paid_social", "display")
NO_TOUCH = "(none)"
MODELS = ("first", "last", "linear", "position")
WEEKS_PER_QUARTER = 13


def load(folder):
    """Read the four raw CSVs from `folder`, rows as dicts of text."""
    out = {}
    for name in ("spend", "touchpoints", "orders", "display_test"):
        with open(os.path.join(folder, name + ".csv"), newline="") as f:
            out[name] = list(csv.DictReader(f))
    return out


def parse_time(text):
    """'2026-08-03 14:05' -> datetime."""
    return datetime.datetime.strptime(text, "%Y-%m-%d %H:%M")


def week_start(time_text):
    """The Monday of the week an event falls in, as 'YYYY-MM-DD'."""
    d = datetime.date.fromisoformat(time_text[:10])
    return (d - datetime.timedelta(days=d.weekday())).isoformat()


def clean_spend(raw_spend):
    """{(week_start, channel): spend including the agency fee}, one value per week and channel.
    Display rows before the week of 17 August 2026 exclude the 15% fee, so they are multiplied by 1.15."""
    out = {}
    for r in raw_spend:
        amount = float(r["spend"])
        if r["channel"] == "display" and r["week_start"] < FEE_CHANGE_WEEK:
            amount *= 1 + FEE
        out[(r["week_start"], r["channel"])] = amount
    return dict(sorted(out.items()))


def clean_orders(raw_orders, start=Q_START, end=Q_END):
    """One row per order_id (the pixel can fire twice), with the order DATE from start to end inclusive.
    Returns dicts with order_id, user_id, order_time, revenue (int), sorted by order_id."""
    seen = {}
    for r in raw_orders:
        if start <= r["order_time"][:10] <= end and r["order_id"] not in seen:
            seen[r["order_id"]] = {"order_id": r["order_id"], "user_id": r["user_id"],
                                   "order_time": r["order_time"], "revenue": int(r["revenue"])}
    return [seen[k] for k in sorted(seen)]


def paths(orders, touches, lookback_days=30):
    """{order_id: [channel, ...]}: the user's touches from lookback_days before the order up to the
    order time (inclusive), oldest first, ties by channel name."""
    by_user = {}
    for t in touches:
        by_user.setdefault(t["user_id"], []).append((t["touch_time"], t["channel"]))
    out = {}
    for o in orders:
        end = parse_time(o["order_time"])
        start = end - datetime.timedelta(days=lookback_days)
        out[o["order_id"]] = [ch for tt, ch in sorted(by_user.get(o["user_id"], []))
                              if start <= parse_time(tt) <= end]
    return out


def weights(path, model):
    """{channel: share of one order} for a path of channels, adding up to 1."""
    if not path:
        return {NO_TOUCH: 1.0}
    n = len(path)
    if model == "first":
        shares = [1.0] + [0.0] * (n - 1)
    elif model == "last":
        shares = [0.0] * (n - 1) + [1.0]
    elif model == "linear":
        shares = [1.0 / n] * n
    elif model == "position":
        if n == 1:
            shares = [1.0]
        elif n == 2:
            shares = [0.5, 0.5]
        else:
            shares = [0.4] + [0.2 / (n - 2)] * (n - 2) + [0.4]
    else:
        raise ValueError("unknown model %r" % model)
    out = {}
    for ch, s in zip(path, shares):
        if s > 0:
            out[ch] = out.get(ch, 0.0) + s
    return out


def attribute(orders, touches, model, lookback_days=30, by_week=False):
    """Credit per channel (or per (week_start, channel) when by_week), adding up to len(orders).
    Orders with no touch in the window go to "(none)"."""
    out = {}
    p = paths(orders, touches, lookback_days)
    for o in orders:
        for ch, share in weights(p[o["order_id"]], model).items():
            key = (week_start(o["order_time"]), ch) if by_week else ch
            out[key] = out.get(key, 0.0) + share
    return dict(sorted(out.items()))


def holdout_lift(test_users, orders, start=TEST_START, end=TEST_END, z=1.96):
    """Conversion (share of users with at least one order dated start to end) for the exposed and
    holdout groups, lift = exposed - holdout with an unpooled (Wald) interval, and
    incremental = lift x exposed users. None if a group is empty."""
    buyers = {o["user_id"] for o in orders if start <= o["order_time"][:10] <= end}
    n = {"exposed": 0, "holdout": 0}
    x = {"exposed": 0, "holdout": 0}
    for u in test_users:
        n[u["grp"]] += 1
        x[u["grp"]] += u["user_id"] in buyers
    if n["exposed"] == 0 or n["holdout"] == 0:
        return None
    pe, ph = x["exposed"] / n["exposed"], x["holdout"] / n["holdout"]
    se = math.sqrt(pe * (1 - pe) / n["exposed"] + ph * (1 - ph) / n["holdout"])
    lift = pe - ph
    return {"n_exposed": n["exposed"], "n_holdout": n["holdout"], "conv_exposed": pe, "conv_holdout": ph,
            "lift": lift, "se": se, "low": lift - z * se, "high": lift + z * se, "incremental": lift * n["exposed"]}


def calibration_factor(test_users, orders, touches, start=TEST_START, end=TEST_END):
    """Incremental display orders in the test / linear-attribution display credit on the orders of
    exposed test users dated start to end. None if that credit is 0 or the test has an empty group."""
    lift = holdout_lift(test_users, orders, start, end)
    exposed = {u["user_id"] for u in test_users if u["grp"] == "exposed"}
    window = [o for o in orders if o["user_id"] in exposed and start <= o["order_time"][:10] <= end]
    credit = attribute(window, touches, "linear").get("display", 0.0)
    if lift is None or credit == 0:
        return None
    return lift["incremental"] / credit


def fit_sqrt_response(points):
    """Least squares through the origin for y = a x sqrt(x): a = sum(y sqrt(x)) / sum(x).
    points: [(weekly spend, weekly conversions), ...]. None if total spend is 0."""
    sx = sum(x for x, _ in points)
    if sx == 0:
        return None
    return sum(y * math.sqrt(x) for x, y in points) / sx


def allocate(a, budget, lower, upper):
    """Split `budget` across channels to maximise sum of a[c] x sqrt(spend[c]), with
    lower[c] <= spend[c] <= upper[c]. Channels with a <= 0 get their lower bound.
    ValueError if the budget is outside [sum of lower, sum of upper]."""
    lo_total, hi_total = sum(lower.values()), sum(upper.values())
    if budget < lo_total - 1e-9 or budget > hi_total + 1e-9:
        raise ValueError("budget outside the bounds")

    def spend_at(lam):
        out = {}
        for c in a:
            want = (a[c] / (2 * lam)) ** 2 if a[c] > 0 else 0.0
            out[c] = min(max(want, lower[c]), upper[c])
        return out

    lo, hi = 1e-12, 1e12
    for _ in range(300):
        mid = math.sqrt(lo * hi)
        if sum(spend_at(mid).values()) > budget:
            lo = mid
        else:
            hi = mid
    return spend_at(math.sqrt(lo * hi))


def plan(spend, orders, touches, test_users, move=0.5):
    """Next quarter's paid budget, by the steps in DELIVERABLES.md. Returns {"calibration", "a",
    "current", "proposed", "current_conversions", "proposed_conversions"} (conversions per quarter)."""
    cal = calibration_factor(test_users, orders, touches)
    weekly = attribute(orders, touches, "linear", by_week=True)
    weeks = sorted({w for w, _ in spend})
    a, current = {}, {}
    for c in PAID:
        factor = cal if c == "display" else 1.0
        pts = [(spend.get((w, c), 0.0), weekly.get((w, c), 0.0) * factor) for w in weeks]
        a[c] = fit_sqrt_response(pts)
        current[c] = sum(x for x, _ in pts)
    budget = sum(current.values())
    lower = {c: current[c] * (1 - move) for c in PAID}
    upper = {c: current[c] * (1 + move) for c in PAID}
    proposed = allocate(a, budget, lower, upper)

    def conversions(s):
        return sum(a[c] * math.sqrt(s[c] / WEEKS_PER_QUARTER) * WEEKS_PER_QUARTER for c in PAID)

    return {"calibration": cal, "a": a, "current": current, "proposed": proposed,
            "current_conversions": conversions(current), "proposed_conversions": conversions(proposed)}


# ---- the deliverable chart ------------------------------------------------

def grouped_bar_svg(groups, series_names, title, width=560, height=280):
    """A plain SVG grouped bar chart: groups = [(label, [value per series]), ...], y axis from 0."""
    colors = ["#9aa5b1", "#3b6ea5"]
    left, top, bottom, right = 80, 50, height - 40, width - 20
    peak = max(v for _, vals in groups for v in vals) * 1.1
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" font-family="sans-serif" font-size="11">'
             % (width, height), '<rect width="100%" height="100%" fill="white"/>',
             '<text x="%d" y="20" font-size="13">%s</text>' % (left, title)]
    for i, name in enumerate(series_names):
        parts.append('<rect x="%d" y="30" width="10" height="10" fill="%s"/>' % (left + 140 * i, colors[i]))
        parts.append('<text x="%d" y="39">%s</text>' % (left + 140 * i + 14, name))
    for i in range(5):
        v = peak * i / 4
        y = bottom - (bottom - top) * i / 4
        parts.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#ddd"/>' % (left, right, y, y))
        parts.append('<text x="%d" y="%.1f" text-anchor="end">%s</text>' % (left - 6, y + 4, "{:,.0f}".format(v)))
    gw = (right - left) / len(groups)
    for g, (label, vals) in enumerate(groups):
        bw = gw * 0.7 / len(vals)
        for i, v in enumerate(vals):
            h = (bottom - top) * v / peak
            x = left + g * gw + gw * 0.15 + i * bw
            parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                         % (x, bottom - h, bw - 2, h, colors[i]))
        parts.append('<text x="%.1f" y="%d" text-anchor="middle">%s</text>' % (left + g * gw + gw / 2, bottom + 16, label))
    parts.append('<line x1="%d" x2="%d" y1="%d" y2="%d" stroke="#333"/>' % (left, right, bottom, bottom))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw = load(os.path.join(here, "data"))
    spend = clean_spend(raw["spend"])
    orders = clean_orders(raw["orders"])
    touches = raw["touchpoints"]
    print("orders: %d raw rows -> %d Q3 orders; spend rows %d -> %d" % (len(raw["orders"]), len(orders),
                                                                         len(raw["spend"]), len(spend)))
    totals = {}
    for (w, c), v in spend.items():
        totals[c] = totals.get(c, 0.0) + v
    print("Q3 spend incl fee", {c: round(v) for c, v in totals.items()})
    for model in MODELS:
        credit = attribute(orders, touches, model)
        print("%-8s" % model, {c: round(v, 1) for c, v in credit.items()})
    lin = attribute(orders, touches, "linear")
    print("CPA linear", {c: round(totals[c] / lin[c]) for c in totals if lin.get(c)})
    lift = holdout_lift(raw["display_test"], orders)
    print("display test", {k: round(v, 4) for k, v in lift.items()})
    p = plan(spend, orders, touches, raw["display_test"])
    print("calibration %.3f" % p["calibration"])
    print("a", {c: round(v, 4) for c, v in p["a"].items()})
    print("current", {c: round(v) for c, v in p["current"].items()}, "conversions %.1f" % p["current_conversions"])
    print("proposed", {c: round(v) for c, v in p["proposed"].items()}, "conversions %.1f" % p["proposed_conversions"])
    svg = grouped_bar_svg([(c, [p["current"][c], p["proposed"][c]]) for c in PAID], ["Q3 spend", "proposed Q4"],
                          "Brambletoe paid spend per quarter, Rs, including fees (synthetic data)")
    with open(os.path.join(here, "solution", "budget_shift.svg"), "w") as f:
        f.write(svg)


if __name__ == "__main__":
    main()
