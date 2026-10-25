"""Exercise: a one page portfolio case, from question to write-up.

load_db, pull, pct, fmt_p and main are done for you. Fill in CHURN_SQL, two_proportion_test
and write_up. Then run: python3 test_lesson.py
"""
import csv
import math
import os
import sqlite3

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
AS_OF = "2026-10-01"
WINDOW = 90

QUESTION = ("Do Pantrybox customers who start on a free trial cancel within 90 days more often "
            "than customers who pay from day one?")

# Only customers with a full 90 days of history, so everyone had the same chance to churn.
# TODO: one row per start_type: start_type, customers, churned.
# Keep only customers whose signup is at least :window days before :as_of.
# churned = cancel_date is not NULL and at most :window days after signup_date.
# Use julianday() for the day differences. Order by start_type.
CHURN_SQL = ""


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
    # TODO: p1, p2, the pooled rate, the pooled standard error, z, the two sided p value
    # (math.erfc(abs(z) / math.sqrt(2))), and a 95% CI for p1 - p2 with the unpooled
    # standard error. Return a dict with keys p1, p2, diff, z, p_value, ci_low, ci_high.
    raise NotImplementedError


def pct(x):
    return "%.1f%%" % (100 * x)


def fmt_p(p):
    return "p < 0.0001" if p < 0.0001 else "p = %.4f" % p


def write_up(groups, test):
    """A one page markdown write-up with the six sections a hiring manager looks for."""
    # TODO: return markdown with a title line and these sections, in this order:
    # ## Question, ## Data, ## Method, ## Result, ## Recommendation, ## Limitations.
    # Result gives "X of N" counts and rates (use pct) for both groups, and the test.
    # Limitations is a list ("- ...") of at least two points, one saying this is not an experiment.
    raise NotImplementedError


def main():
    groups = pull(load_db())
    (nt, ct), (npd, cpd) = groups["trial"], groups["paid"]
    test = two_proportion_test(ct, nt, cpd, npd)
    print(write_up(groups, test))


if __name__ == "__main__":
    main()
