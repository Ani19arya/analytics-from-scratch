"""Case 05: fintech, loan approvals and defaults. Your turn.

Steps 7 to 9 of the case: two SQL queries (SQLite) and the Python that turns
them into an answer. Scores are grouped into 50-point bands named by their
lower bound: band 600 holds scores 600 to 649. Loans run 6 months, so a loan
whose outcome is 'open' has not finished and says nothing yet about default.
"""
import csv
import math
import os
import sqlite3

# ---- given: loading the CSV into SQLite ----------------------------------

COLUMNS = ("app_id", "applied_month", "score", "loan_amount", "decision", "approval_route", "outcome")


def load_db(path):
    """Load applications.csv into an in-memory SQLite table called applications.
    Blank approval_route and outcome become NULL, as they would in a warehouse."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE applications (app_id TEXT, applied_month TEXT, score INTEGER,"
                " loan_amount INTEGER, decision TEXT, approval_route TEXT, outcome TEXT)")
    with open(path, newline="") as f:
        rows = [[r[k] or None for k in COLUMNS] for r in csv.DictReader(f)]
    con.executemany("INSERT INTO applications VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    return con


def query(con, sql):
    """Run sql and return a list of dicts, one per row."""
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


# ---- step 7: SQL ---------------------------------------------------------

# BAND_SQL: one row per 50-point score band that has applicants.
# Columns: band (lower bound: 450, 500, ...), applicants, approved,
# matured (approved loans whose outcome is repaid or defaulted), defaulted,
# default_rate_pct = 100 x defaulted / matured rounded to 1 decimal
# (NULL when nothing has matured), avg_amount = average loan_amount of all
# applicants in the band, rounded to a whole rupee. Order by band.
BAND_SQL = """
-- TODO: your query here
"""

# VINTAGE_SQL: one row per applied_month (a "vintage" is the group of loans
# made in one month). Columns: applied_month, approved, open, matured,
# defaulted, default_rate_pct (as above, NULL when nothing matured).
# Order by applied_month.
VINTAGE_SQL = """
-- TODO: your query here
"""


# ---- step 7 and 9: Python ------------------------------------------------

def wilson(k, n, z=1.96):
    """Wilson 95% interval for a proportion k / n, as (low, high) fractions.
    None when n is 0."""
    # TODO
    raise NotImplementedError


def cutoff_impact(bands, new_cutoff, months, cutoff=650):
    """What lowering the score cutoff from `cutoff` to `new_cutoff` adds.
    bands: rows of BAND_SQL. The bands added are those with
    new_cutoff <= band < cutoff. Their default rate is defaulted / matured
    from the test cell. Per month means divided by `months`.
    Return {"extra_approvals", "extra_defaults", "extra_defaults_low",
    "extra_defaults_high", "marginal_default_rate"} (rates as fractions,
    low and high from the Wilson interval of each band).
    If any added band has no matured loans, return None: we cannot price
    applicants we have never lent to. If no band is added, every value is 0
    and marginal_default_rate is None."""
    # TODO
    raise NotImplementedError


def book_default_rate(bands, cutoff):
    """Expected default rate (a fraction) of everyone approved when the policy
    approves every band >= cutoff: applicants in each band weighted by that
    band's matured default rate. None if no applicant is approved or any
    approved band has no matured loans."""
    # TODO
    raise NotImplementedError


def band_profit(applicants_per_month, avg_amount, default_rate, margin, loss_given_default):
    """Expected profit per month from approving a band: each repaid loan earns
    margin x amount, each default loses loss_given_default x amount."""
    # TODO
    raise NotImplementedError


def break_even_rate(margin, loss_given_default):
    """The default rate at which a loan earns exactly nothing."""
    # TODO
    raise NotImplementedError


# ---- step 8: a chart you can paste into a message ------------------------

def text_chart(bands, width=30):
    """One line per band: '600-649  17.4% #####'. The highest default rate
    gets `width` characters; others are scaled and rounded. A band with no
    matured loans shows 'no data' instead of a rate and a bar."""
    # TODO
    raise NotImplementedError

