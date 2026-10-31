"""Capstone 10-04: Shiftwren subscription and churn. Your submission.

Read BRIEF.md (the request and the data notes) and DELIVERABLES.md (what to
hand in and the exact definitions). This file holds the part of the
deliverable with one right answer: fill in every function, then run
`python3 test_lesson.py`. Standard library only. Keep amounts as floats and
round only where a docstring says so.

Conventions used everywhere below:
- A month is text "YYYY-MM". MRR "at the end of a month" counts every event
  whose effective_on is on or before the last day of that month.
- An account's MRR is the amount on its latest event (a cancel sets it to 0).
- Amounts are EUR a month after cleaning (see the definition change in BRIEF.md).
"""
import csv
import datetime as dt
import os

BASE_MONTH = "2026-09"


# ---- given -----------------------------------

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


# ---- yours ------------------------------------------------------------------

def clean_accounts(rows):
    """{account_id: row} with ids normalised and duplicate accounts dropped (first kept)."""
    # TODO
    raise NotImplementedError


def clean_events(rows, accounts, loaded_by=None, fix_definition=True):
    """Typed, de-duplicated events sorted by (effective_on, event_id).

    loaded_by: keep only rows loaded on or before this date (an as-at view).
    Duplicate event_ids: keep the row loaded last (it carries corrections).
    fix_definition: divide annual amounts requested before 2026-04-01 by 12.
    Each event gets billing (from accounts) and mrr (EUR a month)."""
    # TODO
    raise NotImplementedError


def mrr_by_account(events, month):
    """{account_id: mrr} for accounts paying at the end of the month (mrr > 0)."""
    # TODO
    raise NotImplementedError


def mrr_bridge(events, month):
    """How MRR moved from the end of the previous month to the end of `month`.

    Keys: start_mrr, new, reactivation, expansion, contraction, churn, end_mrr
    (contraction and churn are positive amounts that were lost), start_accounts,
    churned_accounts, logo_churn_pct (churned / start accounts x 100, None if
    no start accounts). start + new + reactivation + expansion - contraction -
    churn = end. New means the account never paid at an earlier month end;
    reactivation means it did, then stopped, and pays again."""
    # TODO
    raise NotImplementedError


def retention_12m(events, month):
    """Gross and net revenue retention over the 12 months to `month`.

    Base: accounts paying at the end of the month 12 months earlier, with that MRR.
    nrr = their MRR now / their MRR then; grr caps each account at its old MRR
    (sum of min(now, then) / then). Both as percentages rounded to 2 decimals,
    None if the base is empty."""
    # TODO
    raise NotImplementedError


def monthly_hazards(events, base_month, window=6):
    """Monthly churn hazard by plan for MONTHLY-billing accounts, fitted on the
    `window` months ending with base_month.

    For each month m in the window: at risk = monthly accounts paying at the end
    of m - 1 (grouped by their plan then); churned = those of them paying 0 at the
    end of m. Returns {plan: {"at_risk", "churned", "hazard"}} plus a "pooled"
    entry over all plans; hazard = churned / at_risk, None when at_risk is 0."""
    # TODO
    raise NotImplementedError


def expansion_rate(events, base_month, window=6):
    """Net expansion of accounts that kept paying, per month, over the `window`
    months ending with base_month: for each month m, accounts paying at the end
    of both m - 1 and m; rate = sum(MRR at end of m - MRR at end of m - 1) /
    sum(MRR at end of m - 1). Upgrades minus downgrades, as a share of the MRR
    that stayed. Returns {"retained_mrr", "net_change", "rate"}, rate None when
    nothing was retained."""
    # TODO
    raise NotImplementedError


def renewal_rate(events, base_month, window=12):
    """Share of ANNUAL accounts that renewed, over renewals due in the `window`
    months ending with base_month. Due in month m: an annual account paying at
    the end of m - 1 whose term started a whole number of years before m.
    Renewed: still paying at the end of m. Returns {"due", "renewed", "rate"},
    rate None when nothing was due."""
    # TODO
    raise NotImplementedError


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
    # TODO
    raise NotImplementedError


def backtest(events, base_month, horizon=6, expansion=True):
    """Forecast from base_month and compare with what the same accounts actually paid.

    actual = MRR at each month end from the accounts paying at the end of
    base_month (all their later events count: churn, changes, reactivation).
    Returns [{"month", "forecast", "actual", "error_pct"}], error_pct =
    100 x (forecast - actual) / actual rounded to 2 decimals."""
    # TODO
    raise NotImplementedError


def reconcile(raw, month):
    """Walk from the MRR finance reported at the close of `month` to the restated MRR.

    reported: finance_close.csv. as_at_close: rebuilt from rows loaded by the
    close cut-off, without the definition fix (must equal reported).
    definition_fix: the change from dividing old annual amounts by 12.
    late_rows: the change from adding rows loaded after the close.
    restated: all rows, fixed. as_at_close + definition_fix + late_rows = restated."""
    # TODO
    raise NotImplementedError
