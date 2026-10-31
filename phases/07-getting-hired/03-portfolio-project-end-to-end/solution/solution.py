"""Solution: a one page portfolio case, from question to write-up and chart."""
import csv
import math
import os
import sqlite3

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
CHART = os.path.join(HERE, "diagram.svg")
AS_OF = "2026-10-01"
TRIAL_DAYS = 14
WINDOW = 90
PARAMS = {"as_of": AS_OF, "trial_days": TRIAL_DAYS, "window": WINDOW}

QUESTION = ("Do Pantrybox customers who start on a free trial cancel more often "
            "than customers who pay from day one?")

# Trial starters who have had their full 14 days, and how many cancelled inside the trial.
CONVERSION_SQL = """
SELECT COUNT(*) AS trial_starters,
       SUM(CASE WHEN cancel_date IS NOT NULL
                 AND julianday(cancel_date) - julianday(signup_date) < :trial_days
                THEN 1 ELSE 0 END) AS never_paid
FROM subscriptions
WHERE start_type = 'trial'
  AND julianday(:as_of) - julianday(signup_date) >= :trial_days
"""

# Paying customers only, with 90 days counted from the first paid day, and only customers
# whose first paid day is at least 90 days before the data date.
CHURN_SQL = """
WITH paying AS (
  SELECT plan, start_type, cancel_date,
         julianday(signup_date) + CASE WHEN start_type = 'trial' THEN :trial_days ELSE 0 END AS first_paid
  FROM subscriptions
  WHERE NOT (start_type = 'trial' AND cancel_date IS NOT NULL
             AND julianday(cancel_date) - julianday(signup_date) < :trial_days)
)
SELECT plan, start_type,
       COUNT(*) AS customers,
       SUM(CASE WHEN cancel_date IS NOT NULL AND julianday(cancel_date) - first_paid <= :window
                THEN 1 ELSE 0 END) AS churned
FROM paying
WHERE julianday(:as_of) - first_paid >= :window
GROUP BY plan, start_type
ORDER BY plan, start_type
"""


def load_db(data_dir=DATA, rows=None):
    """An in-memory database. rows, if given, is a list of
    [customer_id, signup_date, start_type, plan, cancel_date or ''] used instead of the CSV."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE subscriptions (customer_id INTEGER, signup_date TEXT, start_type TEXT, plan TEXT, cancel_date TEXT)")
    if rows is None:
        with open(os.path.join(data_dir, "subscriptions.csv"), newline="") as f:
            rows = [[r["customer_id"], r["signup_date"], r["start_type"], r["plan"], r["cancel_date"]]
                    for r in csv.DictReader(f)]
    con.executemany("INSERT INTO subscriptions VALUES (?, ?, ?, ?, ?)",
                    [(int(r[0]), r[1], r[2], r[3], r[4] or None) for r in rows])
    return con


def conversion(con):
    """(trial_starters, never_paid) from CONVERSION_SQL."""
    n, c = con.execute(CONVERSION_SQL, PARAMS).fetchone()
    return (n, c or 0)


def pull(con):
    """{(plan, start_type): (customers, churned)} from CHURN_SQL."""
    return {(plan, t): (n, c) for plan, t, n, c in con.execute(CHURN_SQL, PARAMS).fetchall()}


def by_start(groups):
    """Add the plans together: {start_type: (customers, churned)}."""
    out = {}
    for (_, t), (n, c) in groups.items():
        n0, c0 = out.get(t, (0, 0))
        out[t] = (n0 + n, c0 + c)
    return out


def two_proportion_test(x1, n1, x2, n2):
    """Two sided z test for p1 - p2, plus a 95% confidence interval for the difference."""
    p1, p2 = x1 / n1, x2 / n2
    pooled = (x1 + x2) / (n1 + n2)
    se_pooled = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    diff = p1 - p2
    if se_pooled == 0:
        # Both groups all churned or none did: no evidence of a gap.
        z, p_value = 0.0, 1.0
    else:
        z = diff / se_pooled
        p_value = math.erfc(abs(z) / math.sqrt(2))
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    return {"p1": p1, "p2": p2, "diff": diff, "z": z, "p_value": p_value,
            "ci_low": diff - 1.96 * se, "ci_high": diff + 1.96 * se}


def pct(x):
    return "%.1f%%" % (100 * x)


def pts(x):
    return "%.1f" % (100 * x)


def fmt_p(p):
    return "p < 0.0001" if p < 0.0001 else "p = %.4f" % p


def write_up(conv, groups, test, chart="diagram.svg"):
    """A one page markdown write-up with the six sections a hiring manager looks for.
    chart is the file name of the chart image the page shows."""
    starters, never = conv
    g = by_start(groups)
    nt, ct = g["trial"]
    npd, cpd = g["paid"]
    clear = test["p_value"] < 0.05
    if clear and test["diff"] > 0:
        verdict = ("Paying customers who came through the trial churned more: a gap of %s points "
                   "(95%% CI %s to %s, z = %.2f, %s)."
                   % (pts(test["diff"]), pts(test["ci_low"]), pts(test["ci_high"]), test["z"], fmt_p(test["p_value"])))
        rec = ("Keep the trial, and add a check in for trial converters in their first 30 paid days. "
               "Before changing the trial itself, run an A/B test, because this comparison is not one.")
    else:
        verdict = ("The paid churn gap of %s points is not clear of noise "
                   "(95%% CI %s to %s points, z = %.2f, %s)."
                   % (pts(test["diff"]), pts(test["ci_low"]), pts(test["ci_high"]), test["z"], fmt_p(test["p_value"])))
        rec = ("Do not cut the trial on churn grounds: once customers pay, the churn gap between trial and paid "
               "starters is not clear of noise. The clear loss is inside the trial, so work on trial conversion "
               "first, and test any change to the trial with an A/B test.")
    plan_lines, same_way = [], True
    for plan in sorted({p for p, _ in groups}, reverse=True):
        parts, rates = [], {}
        for t in ("trial", "paid"):
            n, c = groups.get((plan, t), (0, 0))
            rates[t] = c / n if n else None
            parts.append("%s %d of %d (%s)" % (t, c, n, pct(c / n) if n else "n/a"))
        plan_lines.append("- %s plan: %s." % (plan.capitalize(), ", ".join(parts)))
        if None in rates.values() or (rates["trial"] - rates["paid"]) * test["diff"] <= 0:
            same_way = False
    plan_intro = ("Within each plan the gap points the same way, so plan mix does not explain it:" if same_way
                  else "Within the plans the gap does not point the same way, so plan mix matters:")
    lines = [
        "# Free trials and churn at Pantrybox",
        "",
        "## Question",
        QUESTION,
        "",
        "## Data",
        "One table of Pantrybox customers as of %s. A trial lasts %d days; a trial starter who cancels "
        "inside it never paid. Paid churn means a cancel within %d days of the first paid day, for customers "
        "whose first paid day is at least %d days before the data date: %d trial converters and %d paid starters."
        % (AS_OF, TRIAL_DAYS, WINDOW, WINDOW, nt, npd),
        "",
        "## Method",
        "Two SQL queries: one counts trial starters who cancelled inside the trial, one counts paying customers "
        "and %d day cancellations by plan and start type. A two proportion z test compares the paid churn rates, "
        "with a 95%% confidence interval for the difference." % WINDOW,
        "",
        "## Result",
        "Trial conversion: %d of %d trial starters cancelled inside the trial and never paid (%s), so %s converted."
        % (never, starters, pct(never / starters), pct(1 - never / starters)),
        "",
        "Paid churn: trial converters %d of %d (%s), paid starters %d of %d (%s). %s"
        % (ct, nt, pct(test["p1"]), cpd, npd, pct(test["p2"]), verdict),
        "",
        plan_intro,
    ] + plan_lines + [
        "",
        "![Paid churn by plan and start type](%s)" % chart,
        "",
        "## Recommendation",
        rec,
        "",
        "## Limitations",
        "- This is an observational comparison, not an experiment: customers chose how to start, "
        "so a gap may come from who they are, not from the trial.",
        "- Customers whose first paid day is less than %d days old are left out, because their outcome "
        "is not known yet." % WINDOW,
        "- The annual groups are small, so their rates are uncertain.",
    ]
    return "\n".join(lines) + "\n"


# ---- the chart (stdlib only: the SVG is plain text) -------------------------

COLOURS = {"trial": "#2f6db5", "paid": "#c4622d"}


def rate_interval(c, n):
    """A 95% interval for one rate, c of n, clipped to 0 and 1."""
    p = c / n
    half = 1.96 * math.sqrt(p * (1 - p) / n)
    return max(0.0, p - half), min(1.0, p + half)


def churn_chart_svg(groups):
    """A grouped bar chart of paid churn by plan and start type, with 95% interval whiskers."""
    width, height = 560, 360
    left, right, top, bottom = 60, 20, 50, 80
    plot_w, plot_h = width - left - right, height - top - bottom
    plans = sorted({p for p, _ in groups}, reverse=True)
    highest = max(rate_interval(c, n)[1] for n, c in groups.values() if n)
    y_max = math.ceil(highest * 10) / 10
    y = lambda v: top + plot_h * (1 - v / y_max)
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
           'font-family="Helvetica, Arial, sans-serif" font-size="12">' % (width, height, width, height),
           '<rect width="%d" height="%d" fill="#ffffff"/>' % (width, height),
           '<text x="%d" y="22" font-size="15" font-weight="bold" fill="#222222">'
           'Paid churn within %d days of the first paid day</text>' % (left, WINDOW),
           '<text x="%d" y="38" fill="#555555">Pantrybox, synthetic data. Whiskers: 95%% interval.</text>' % left]
    step = 0.1
    v = 0.0
    while v <= y_max + 1e-9:
        out.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#dddddd"/>' % (left, width - right, y(v), y(v)))
        out.append('<text x="%d" y="%.1f" text-anchor="end" fill="#555555">%d%%</text>' % (left - 6, y(v) + 4, round(v * 100)))
        v += step
    group_w = plot_w / len(plans)
    bar_w = 70
    for i, plan in enumerate(plans):
        cx = left + group_w * (i + 0.5)
        for j, t in enumerate(("trial", "paid")):
            n, c = groups.get((plan, t), (0, 0))
            if not n:
                continue
            p = c / n
            lo, hi = rate_interval(c, n)
            x = cx + (j - 1) * (bar_w + 8) + 4
            out.append('<rect x="%.1f" y="%.1f" width="%d" height="%.1f" fill="%s">'
                       '<title>%s, %s: %s (%d of %d)</title></rect>'
                       % (x, y(p), bar_w, y(0) - y(p), COLOURS[t], plan, t, pct(p), c, n))
            mid = x + bar_w / 2
            out.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="#222222" stroke-width="1.5"/>'
                       % (mid, mid, y(lo), y(hi)))
            for edge in (lo, hi):
                out.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="#222222" stroke-width="1.5"/>'
                           % (mid - 8, mid + 8, y(edge), y(edge)))
            out.append('<text x="%.1f" y="%.1f" text-anchor="middle" fill="#222222" font-weight="bold">%s</text>'
                       % (mid, y(0) + 15, pct(p)))
        out.append('<text x="%.1f" y="%d" text-anchor="middle" fill="#222222">%s plan</text>'
                   % (cx, height - bottom + 34, plan.capitalize()))
    lx = left
    for t, label in (("trial", "Started on a free trial"), ("paid", "Paid from day one")):
        out.append('<rect x="%d" y="%d" width="12" height="12" fill="%s"/>' % (lx, height - 22, COLOURS[t]))
        out.append('<text x="%d" y="%d" fill="#222222">%s</text>' % (lx + 18, height - 12, label))
        lx += 200
    out.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#222222"/>' % (left, width - right, y(0), y(0)))
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    con = load_db()
    conv, groups = conversion(con), pull(con)
    g = by_start(groups)
    test = two_proportion_test(g["trial"][1], g["trial"][0], g["paid"][1], g["paid"][0])
    with open(CHART, "w") as f:
        f.write(churn_chart_svg(groups))
    print(write_up(conv, groups, test))


if __name__ == "__main__":
    main()
