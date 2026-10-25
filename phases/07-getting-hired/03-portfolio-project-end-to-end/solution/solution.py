"""Solution: a one page portfolio case, from question to write-up."""
import csv
import math
import os
import sqlite3

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
AS_OF = "2026-10-01"
WINDOW = 90

QUESTION = ("Do Pantrybox customers who start on a free trial cancel within 90 days more often "
            "than customers who pay from day one?")

# Only customers with a full 90 days of history, so everyone had the same chance to churn.
CHURN_SQL = """
SELECT start_type,
       COUNT(*) AS customers,
       SUM(CASE WHEN cancel_date IS NOT NULL
                 AND julianday(cancel_date) - julianday(signup_date) <= :window
                THEN 1 ELSE 0 END) AS churned
FROM subscriptions
WHERE julianday(:as_of) - julianday(signup_date) >= :window
GROUP BY start_type
ORDER BY start_type
"""


def load_db(data_dir=DATA):
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE subscriptions (customer_id INTEGER, signup_date TEXT, start_type TEXT, plan TEXT, cancel_date TEXT)")
    with open(os.path.join(data_dir, "subscriptions.csv"), newline="") as f:
        rows = [(int(r["customer_id"]), r["signup_date"], r["start_type"], r["plan"], r["cancel_date"] or None)
                for r in csv.DictReader(f)]
    con.executemany("INSERT INTO subscriptions VALUES (?, ?, ?, ?, ?)", rows)
    return con


def pull(con):
    """{start_type: (customers, churned)} from CHURN_SQL."""
    cur = con.execute(CHURN_SQL, {"as_of": AS_OF, "window": WINDOW})
    return {t: (n, c) for t, n, c in cur.fetchall()}


def two_proportion_test(x1, n1, x2, n2):
    """Two sided z test for p1 - p2, plus a 95% confidence interval for the difference."""
    p1, p2 = x1 / n1, x2 / n2
    pooled = (x1 + x2) / (n1 + n2)
    se_pooled = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se_pooled
    p_value = math.erfc(abs(z) / math.sqrt(2))
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    diff = p1 - p2
    return {"p1": p1, "p2": p2, "diff": diff, "z": z, "p_value": p_value,
            "ci_low": diff - 1.96 * se, "ci_high": diff + 1.96 * se}


def pct(x):
    return "%.1f%%" % (100 * x)


def fmt_p(p):
    return "p < 0.0001" if p < 0.0001 else "p = %.4f" % p


def write_up(groups, test):
    """A one page markdown write-up with the six sections a hiring manager looks for."""
    nt, ct = groups["trial"]
    npd, cpd = groups["paid"]
    significant = test["p_value"] < 0.05
    if significant and test["diff"] > 0:
        result_line = ("Trial starters churned more: %s against %s, a gap of %s points "
                       "(95%% CI %s to %s, z = %.2f, %s)."
                       % (pct(test["p1"]), pct(test["p2"]), "%.1f" % (100 * test["diff"]),
                          "%.1f" % (100 * test["ci_low"]), "%.1f" % (100 * test["ci_high"]), test["z"], fmt_p(test["p_value"])))
        rec = ("Keep the trial for acquisition, but treat trial customers as a separate group: "
               "add a check in during days 1 to 30 and measure 90 day churn for trial starters every month. "
               "Before changing the trial itself, run an A/B test, because this comparison is not one.")
    else:
        result_line = ("The gap between trial (%s) and paid (%s) is not clear of noise "
                       "(95%% CI %s to %s points, %s)."
                       % (pct(test["p1"]), pct(test["p2"]), "%.1f" % (100 * test["ci_low"]),
                          "%.1f" % (100 * test["ci_high"]), fmt_p(test["p_value"])))
        rec = "Do not change the trial on this evidence. Collect another quarter of signups and repeat."
    lines = [
        "# Trial starters and 90 day churn at Pantrybox",
        "",
        "## Question",
        QUESTION,
        "",
        "## Data",
        "%d customers who signed up at least %d days before %s: %d trial starters and %d paid starters. "
        "Churn means a cancel date within %d days of signup." % (nt + npd, WINDOW, AS_OF, nt, npd, WINDOW),
        "",
        "## Method",
        "A SQL query counts customers and 90 day cancellations by start type. "
        "A two proportion z test compares the churn rates, with a 95% confidence interval for the difference.",
        "",
        "## Result",
        "Trial: %d of %d churned (%s). Paid: %d of %d churned (%s)." % (ct, nt, pct(test["p1"]), cpd, npd, pct(test["p2"])),
        result_line,
        "",
        "## Recommendation",
        rec,
        "",
        "## Limitations",
        "- This is an observational comparison, not an experiment: customers chose how to start, "
        "so the gap may come from who they are, not from the trial.",
        "- Plan also drives churn (annual customers cancel less), so the comparison should be repeated within each plan.",
        "- Customers who signed up in the last 90 days are left out because their outcome is not known yet.",
    ]
    return "\n".join(lines) + "\n"


def main():
    groups = pull(load_db())
    (nt, ct), (npd, cpd) = groups["trial"], groups["paid"]
    test = two_proportion_test(ct, nt, cpd, npd)
    print(write_up(groups, test))


if __name__ == "__main__":
    main()
