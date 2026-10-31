"""Exercise: a one page portfolio case, from question to write-up and chart.

load_db, conversion, pull, by_start, pct, pts, fmt_p, the chart code and main are done for you.
Fill in CONVERSION_SQL, CHURN_SQL, two_proportion_test and write_up.
Then run: python3 test_lesson.py
"""
import csv
import math
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
# Your chart goes to my_diagram.svg, so the committed diagram.svg stays as the reference.
CHART = os.path.join(HERE, "my_diagram.svg")
AS_OF = "2026-10-01"
TRIAL_DAYS = 14
WINDOW = 90
PARAMS = {"as_of": AS_OF, "trial_days": TRIAL_DAYS, "window": WINDOW}

QUESTION = ("Do Pantrybox customers who start on a free trial cancel more often "
            "than customers who pay from day one?")

# TODO: one row: trial_starters, never_paid.
# Keep trial starters whose signup is at least :trial_days days before :as_of (they had the
# whole trial). never_paid = cancel_date is not NULL and less than :trial_days days after signup.
CONVERSION_SQL = ""

# TODO: one row per plan and start_type: plan, start_type, customers, churned.
# Paying customers only: leave out trial starters who cancelled inside the trial.
# first paid day = signup_date for paid starters, signup_date + :trial_days for trial starters
#   (in SQLite: julianday(signup_date) + CASE WHEN start_type = 'trial' THEN :trial_days ELSE 0 END).
# Keep customers whose first paid day is at least :window days before :as_of.
# churned = cancel_date is not NULL and at most :window days after the first paid day.
# Order by plan, start_type. Hint: a CTE (WITH paying AS (...)) keeps it readable.
CHURN_SQL = ""


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
    # TODO: p1, p2, the pooled rate, the pooled standard error, z, the two sided p value
    # (math.erfc(abs(z) / math.sqrt(2))), and a 95% CI for p1 - p2 with the unpooled
    # standard error. If the pooled standard error is 0 (nobody churned, or everybody did),
    # return z = 0.0 and p_value = 1.0 instead of dividing by zero.
    # Return a dict with keys p1, p2, diff, z, p_value, ci_low, ci_high.
    raise NotImplementedError


def pct(x):
    return "%.1f%%" % (100 * x)


def pts(x):
    return "%.1f" % (100 * x)


def fmt_p(p):
    return "p < 0.0001" if p < 0.0001 else "p = %.4f" % p


def write_up(conv, groups, test, chart="diagram.svg"):
    """A one page markdown write-up with the six sections a hiring manager looks for.
    chart is the file name of the chart image the page shows."""
    # TODO: return markdown with a title line and these sections, in this order:
    # ## Question, ## Data, ## Method, ## Result, ## Recommendation, ## Limitations.
    # Result gives:
    #   trial conversion as "X of N" never paid, with the rate (use pct),
    #   paid churn as "X of N" and the rate for trial converters and for paid starters, and the test,
    #   one line per plan with "X of N" for both start types (by_start adds plans together),
    #   the chart: "![Paid churn by plan and start type](%s)" % chart
    # Limitations is a list ("- ...") of at least two points, one saying this is not an experiment.
    raise NotImplementedError


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
    print(write_up(conv, groups, test, chart="my_diagram.svg"))


if __name__ == "__main__":
    main()
