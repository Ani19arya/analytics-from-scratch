"""Capstone 10-04: Shiftwren subscription and churn. Worked solution.

Read DELIVERABLES.md for what each function must return, and solution/WRITEUP.md
for the reasoning and the write-up built from these numbers. Run it from the
capstone folder: python3 solution/solution.py (prints the numbers and writes
solution/mrr_forecast.svg).

Conventions used everywhere below:
- A month is text "YYYY-MM". MRR "at the end of a month" counts every event
  whose effective_on is on or before the last day of that month.
- An account's MRR is the amount on its latest event (a cancel sets it to 0).
- Amounts are EUR a month. For annual accounts, events requested before
  2026-04-01 hold the annual contract value, so they are divided by 12.
"""
import csv
import datetime as dt
import os

SWITCH = "2026-04-01"
BASE_MONTH = "2026-09"


# ---- helpers (given in the exercise too) -----------------------------------

def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_raw(folder):
    """The three tables as lists of dicts of text, exactly as in the CSVs."""
    return {name: read_csv(os.path.join(folder, name + ".csv"))
            for name in ("accounts", "subscription_events", "finance_close")}


def month_index(month):
    return int(month[:4]) * 12 + int(month[5:7]) - 1


def month_name(i):
    return "%04d-%02d" % (i // 12, i % 12 + 1)


def add_months(month, n):
    return month_name(month_index(month) + n)


def month_end(month):
    i = month_index(month) + 1
    return (dt.date(i // 12, i % 12 + 1, 1) - dt.timedelta(days=1)).isoformat()


def close_cutoff(month):
    """The close for a month used rows loaded by the 3rd of the next month."""
    return add_months(month, 1) + "-03"


# ---- yours: step 1, clean -----------------------------------------------------

def norm_id(account_id):
    return account_id.strip().upper()


def clean_accounts(rows):
    """{account_id: row} with ids normalised and duplicate accounts dropped (first kept)."""
    out = {}
    for r in rows:
        aid = norm_id(r["account_id"])
        if aid not in out:
            out[aid] = dict(r, account_id=aid)
    return out


def clean_events(rows, accounts, loaded_by=None, fix_definition=True):
    """Typed, de-duplicated events sorted by (effective_on, event_id).

    loaded_by: keep only rows loaded on or before this date (an as-at view).
    Duplicate event_ids: keep the row loaded last (it carries corrections).
    fix_definition: divide annual amounts requested before 2026-04-01 by 12.
    Each event gets billing (from accounts) and mrr (EUR a month)."""
    best = {}
    for r in rows:
        if loaded_by is not None and r["loaded_on"] > loaded_by:
            continue
        cur = best.get(r["event_id"])
        if cur is None or r["loaded_on"] >= cur["loaded_on"]:
            best[r["event_id"]] = r
    out = []
    for r in best.values():
        aid = norm_id(r["account_id"])
        billing = accounts[aid]["billing"]
        amount = int(r["amount"])
        if fix_definition and billing == "annual" and r["requested_on"] < SWITCH:
            amount = amount / 12.0
        out.append({"event_id": r["event_id"], "account_id": aid, "event_type": r["event_type"],
                    "plan": r["plan"], "billing": billing, "mrr": amount,
                    "requested_on": r["requested_on"], "effective_on": r["effective_on"]})
    out.sort(key=lambda e: (e["effective_on"], e["event_id"]))
    return out


# ---- step 2: MRR and the bridge -------------------------------------------

def account_state(events, month):
    """{account_id: event} with each account's latest event effective by the month end."""
    end = month_end(month)
    state = {}
    for e in events:
        if e["effective_on"] <= end:
            state[e["account_id"]] = e
    return state


def mrr_by_account(events, month):
    """{account_id: mrr} for accounts paying at the end of the month (mrr > 0)."""
    return {a: e["mrr"] for a, e in account_state(events, month).items() if e["mrr"] > 0}


def mrr_bridge(events, month):
    """How MRR moved from the end of the previous month to the end of `month`.

    Keys: start_mrr, new, reactivation, expansion, contraction, churn, end_mrr
    (contraction and churn are positive amounts that were lost), start_accounts,
    churned_accounts, logo_churn_pct (churned / start accounts x 100, None if
    no start accounts). start + new + reactivation + expansion - contraction -
    churn = end. New means the account never paid at an earlier month end;
    reactivation means it did, then stopped, and pays again."""
    prev = mrr_by_account(events, add_months(month, -1))
    cur = mrr_by_account(events, month)
    paid_before = set()
    # an account "paid before" if it had MRR > 0 at any earlier month end
    first = min((e["effective_on"][:7] for e in events), default=month)
    m = first
    while month_index(m) < month_index(month):
        paid_before.update(mrr_by_account(events, m))
        m = add_months(m, 1)
    out = {"start_mrr": sum(prev.values()), "new": 0.0, "reactivation": 0.0, "expansion": 0.0,
           "contraction": 0.0, "churn": 0.0, "end_mrr": sum(cur.values())}
    churned = 0
    for a in set(prev) | set(cur):
        p, c = prev.get(a, 0), cur.get(a, 0)
        if p == 0:
            out["reactivation" if a in paid_before else "new"] += c
        elif c == 0:
            out["churn"] += p
            churned += 1
        elif c > p:
            out["expansion"] += c - p
        else:
            out["contraction"] += p - c
    out = {k: round(v, 2) for k, v in out.items()}
    out["start_accounts"] = len(prev)
    out["churned_accounts"] = churned
    out["logo_churn_pct"] = round(100.0 * churned / len(prev), 2) if prev else None
    return out


def retention_12m(events, month):
    """Gross and net revenue retention over the 12 months to `month`.

    Base: accounts paying at the end of the month 12 months earlier, with that MRR.
    nrr = their MRR now / their MRR then; grr caps each account at its old MRR
    (sum of min(now, then) / then). Both as percentages rounded to 2 decimals,
    None if the base is empty."""
    then = mrr_by_account(events, add_months(month, -12))
    now = mrr_by_account(events, month)
    base = sum(then.values())
    if not base:
        return {"base_mrr": 0, "grr_pct": None, "nrr_pct": None}
    kept = sum(min(now.get(a, 0), v) for a, v in then.items())
    total = sum(now.get(a, 0) for a in then)
    return {"base_mrr": round(base, 2), "grr_pct": round(100.0 * kept / base, 2),
            "nrr_pct": round(100.0 * total / base, 2)}


# ---- step 3: the churn model -----------------------------------------------

def monthly_hazards(events, base_month, window=6):
    """Monthly churn hazard by plan for MONTHLY-billing accounts, fitted on the
    `window` months ending with base_month.

    For each month m in the window: at risk = monthly accounts paying at the end
    of m - 1 (grouped by their plan then); churned = those of them paying 0 at the
    end of m. Returns {plan: {"at_risk", "churned", "hazard"}} plus a "pooled"
    entry over all plans; hazard = churned / at_risk, None when at_risk is 0."""
    out = {}
    for k in range(window - 1, -1, -1):
        m = add_months(base_month, -k)
        before = account_state(events, add_months(m, -1))
        after = mrr_by_account(events, m)
        for a, e in before.items():
            if e["billing"] != "monthly" or e["mrr"] <= 0:
                continue
            for key in (e["plan"], "pooled"):
                row = out.setdefault(key, {"at_risk": 0, "churned": 0})
                row["at_risk"] += 1
                row["churned"] += a not in after
    for row in out.values():
        row["hazard"] = row["churned"] / row["at_risk"] if row["at_risk"] else None
    return out


def expansion_rate(events, base_month, window=6):
    """Net expansion of accounts that kept paying, per month, over the `window`
    months ending with base_month: for each month m, accounts paying at the end
    of both m - 1 and m; rate = sum(MRR at end of m - MRR at end of m - 1) /
    sum(MRR at end of m - 1). Upgrades minus downgrades, as a share of the MRR
    that stayed. Returns {"retained_mrr", "net_change", "rate"}, rate None when
    nothing was retained."""
    base = change = 0.0
    for k in range(window - 1, -1, -1):
        m = add_months(base_month, -k)
        before = mrr_by_account(events, add_months(m, -1))
        after = mrr_by_account(events, m)
        for a, v in before.items():
            if a in after:
                base += v
                change += after[a] - v
    return {"retained_mrr": round(base, 2), "net_change": round(change, 2),
            "rate": change / base if base else None}


def term_start(events, account_id, month):
    """effective_on of the account's latest start or reactivate event by the month end."""
    end = month_end(month)
    out = None
    for e in events:
        if e["account_id"] == account_id and e["event_type"] in ("start", "reactivate") and e["effective_on"] <= end:
            out = e["effective_on"]
    return out


def is_anniversary(start_date, month):
    k = month_index(month) - month_index(start_date[:7])
    return k > 0 and k % 12 == 0


def renewal_rate(events, base_month, window=12):
    """Share of ANNUAL accounts that renewed, over renewals due in the `window`
    months ending with base_month. Due in month m: an annual account paying at
    the end of m - 1 whose term started a whole number of years before m.
    Renewed: still paying at the end of m. Returns {"due", "renewed", "rate"},
    rate None when nothing was due."""
    due = renewed = 0
    for k in range(window - 1, -1, -1):
        m = add_months(base_month, -k)
        before = account_state(events, add_months(m, -1))
        after = mrr_by_account(events, m)
        for a, e in before.items():
            if e["billing"] == "annual" and e["mrr"] > 0 and is_anniversary(term_start(events, a, add_months(m, -1)), m):
                due += 1
                renewed += a in after
    return {"due": due, "renewed": renewed, "rate": renewed / due if due else None}


def forecast(events, base_month, horizon=6, window=6, renewal_window=12, expansion=True):
    """Expected MRR of the accounts paying at the end of base_month, for each of
    the next `horizon` month ends. No new sales and no reactivations.

    Monthly account on plan p: MRR x (1 - h_p) ** k after k months, h_p from
    monthly_hazards (the pooled hazard when the plan has none).
    Annual account: full MRR until its next anniversary month, then MRR x the
    renewal rate (ValueError if a renewal falls in the horizon and the rate is None).
    expansion=True multiplies every month's total by (1 + g) ** k, g from
    expansion_rate (0 when None); expansion=False is the churn-only model.
    Returns [(month, expected_mrr rounded to 2 decimals), ...]."""
    hz = monthly_hazards(events, base_month, window)
    pooled = hz.get("pooled", {}).get("hazard") or 0.0
    rr = renewal_rate(events, base_month, renewal_window)["rate"]
    g = (expansion_rate(events, base_month, window)["rate"] or 0.0) if expansion else 0.0
    book = account_state(events, base_month)
    out = []
    for k in range(1, horizon + 1):
        m = add_months(base_month, k)
        total = 0.0
        for a, e in book.items():
            if e["mrr"] <= 0:
                continue
            if e["billing"] == "monthly":
                h = hz.get(e["plan"], {}).get("hazard")
                h = pooled if h is None else h
                total += e["mrr"] * (1 - h) ** k
            else:
                start = term_start(events, a, base_month)
                renews = any(is_anniversary(start, add_months(base_month, j)) for j in range(1, k + 1))
                if renews and rr is None:
                    raise ValueError("an annual renewal falls in the horizon but no renewal rate was observed")
                total += e["mrr"] * (rr if renews else 1.0)
        out.append((m, round(total * (1 + g) ** k, 2)))
    return out


def backtest(events, base_month, horizon=6, expansion=True):
    """Forecast from base_month and compare with what the same accounts actually paid.

    actual = MRR at each month end from the accounts paying at the end of
    base_month (all their later events count: churn, changes, reactivation).
    Returns [{"month", "forecast", "actual", "error_pct"}], error_pct =
    100 x (forecast - actual) / actual rounded to 2 decimals."""
    book = set(mrr_by_account(events, base_month))
    out = []
    for m, f in forecast(events, base_month, horizon, expansion=expansion):
        actual = round(sum(v for a, v in mrr_by_account(events, m).items() if a in book), 2)
        out.append({"month": m, "forecast": f, "actual": actual,
                    "error_pct": round(100.0 * (f - actual) / actual, 2) if actual else None})
    return out


# ---- step 4: reconcile with what finance reported ----------------------------

def reconcile(raw, month):
    """Walk from the MRR finance reported at the close of `month` to the restated MRR.

    reported: finance_close.csv. as_at_close: rebuilt from rows loaded by the
    close cut-off, without the definition fix (must equal reported).
    definition_fix: the change from dividing old annual amounts by 12.
    late_rows: the change from adding rows loaded after the close.
    restated: all rows, fixed. as_at_close + definition_fix + late_rows = restated."""
    accounts = clean_accounts(raw["accounts"])
    cut = close_cutoff(month)

    def total(loaded_by, fix):
        return sum(mrr_by_account(clean_events(raw["subscription_events"], accounts, loaded_by, fix), month).values())

    reported = next(int(r["reported_mrr"]) for r in raw["finance_close"] if r["month"] == month)
    a = total(cut, False)
    b = total(cut, True)
    c = total(None, True)
    return {"reported": reported, "as_at_close": round(a, 2), "definition_fix": round(b - a, 2),
            "late_rows": round(c - b, 2), "restated": round(c, 2)}


# ---- the deliverable: printed numbers and one chart ----------------------------

def text_bar(value, top, width=30):
    return "#" * int(round(width * value / top)) if top else ""


def bar_chart_svg(series, first_forecast, title, width=640, height=280):
    """Bars from zero; months from first_forecast on are drawn lighter (forecast)."""
    left, bottom, top_pad = 56, 40, 34
    top = max(v for _, v in series) or 1
    step = 10 ** (len(str(int(top))) - 1)
    ymax = (int(top // step) + 1) * step
    bw = (width - left - 10) / float(len(series))
    plot_h = height - bottom - top_pad
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" font-family="sans-serif" '
             'font-size="10">' % (width, height),
             '<rect width="100%%" height="100%%" fill="#ffffff"/>',
             '<text x="%d" y="18" font-size="13" fill="#222">%s</text>' % (left, title)]
    for i in range(5):
        v = ymax * i / 4.0
        y = height - bottom - plot_h * i / 4.0
        parts.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#ddd"/>' % (left, width - 10, y, y))
        parts.append('<text x="%d" y="%.1f" text-anchor="end" fill="#555">%s</text>' % (left - 4, y + 3, "{:,.0f}".format(v)))
    for i, (label, v) in enumerate(series):
        h = plot_h * v / ymax
        x = left + i * bw + 2
        colour = "#9ecae1" if label >= first_forecast else "#3182bd"
        parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="%s"/>'
                     % (x, height - bottom - h, bw - 4, h, colour))
        if i % 3 == 0 or label == first_forecast:
            parts.append('<text x="%.1f" y="%d" text-anchor="middle" fill="#555">%s</text>'
                         % (x + (bw - 4) / 2, height - bottom + 14, label))
    parts.append('<text x="%d" y="%d" fill="#555">Dark: restated actual. Light: expected MRR of the September '
                 'book (no new sales). Synthetic data.</text>' % (left, height - 8))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main(folder=None):
    folder = folder or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    raw = load_raw(folder)
    accounts = clean_accounts(raw["accounts"])
    events = clean_events(raw["subscription_events"], accounts)
    print("Restated MRR bridge, last 6 months (EUR)")
    for k in range(5, -1, -1):
        m = add_months(BASE_MONTH, -k)
        b = mrr_bridge(events, m)
        print(" ", m, b)
    print("12-month retention to", BASE_MONTH, retention_12m(events, BASE_MONTH))
    print("Monthly hazards:", {k: round(v["hazard"], 4) for k, v in monthly_hazards(events, BASE_MONTH).items()})
    print("Renewal rate:", renewal_rate(events, BASE_MONTH))
    print("Expansion:", expansion_rate(events, BASE_MONTH))
    print("Backtest from 2026-03, churn only, then with expansion:")
    for r in backtest(events, "2026-03", expansion=False):
        print(" ", r)
    for r in backtest(events, "2026-03"):
        print(" ", r)
    print("Forecast of the September book:")
    fc = forecast(events, BASE_MONTH)
    top = max(v for _, v in fc)
    for m, v in fc:
        print("  %s %10.2f %s" % (m, v, text_bar(v, top)))
    print("Reconcile September:", reconcile(raw, BASE_MONTH))
    history = []
    m = "2025-01"
    while month_index(m) <= month_index(BASE_MONTH):
        history.append((m, sum(mrr_by_account(events, m).values())))
        m = add_months(m, 1)
    svg = bar_chart_svg(history + fc, add_months(BASE_MONTH, 1), "Shiftwren MRR, EUR a month, restated")
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mrr_forecast.svg"), "w") as f:
        f.write(svg)


if __name__ == "__main__":
    main()
