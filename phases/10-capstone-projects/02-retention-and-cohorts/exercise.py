"""Capstone 10-02: Chordwhistle retention and cohorts. Your submission.

Read BRIEF.md (the request and the notes from the data team) and DELIVERABLES.md
(what to hand in, with the definitions). This file holds the part of the
deliverable with one right answer: fill in every function, then run
`python3 test_lesson.py`. Standard library only. Months are 'YYYY-MM' text.
"""
import csv
import os

LAST_COMPLETE_MONTH = "2026-09"

# ---- given ----------------------------------------------------------------


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


# ---- yours ----------------------------------------------------------------

def clean_users(raw_users):
    """{user_id: {"signup_month", "platform", "source"}}: one entry per real user."""
    # TODO
    raise NotImplementedError


def active_months(raw_activity, users, last_month=LAST_COMPLETE_MONTH):
    """{user_id: set of 'YYYY-MM' months the user was active}, for every user in `users`,
    using the activity definition in DELIVERABLES.md, months from sign-up up to `last_month`."""
    # TODO
    raise NotImplementedError


def retention_matrix(users, active, last_month=LAST_COMPLETE_MONTH):
    """{cohort month: {"size", "active": [users active at month 0, 1, ...], "rates": [...]}}.
    Lists stop at the last observed month for that cohort."""
    # TODO
    raise NotImplementedError


def pooled_curve(matrix):
    """[retention at month 0, 1, ...], each pooled over the cohorts observed at that month."""
    # TODO
    raise NotImplementedError


def shortfall(matrix, k=1):
    """[(cohort, users_lost), ...] biggest first, ties by cohort. See DELIVERABLES.md for users_lost."""
    # TODO
    raise NotImplementedError


def two_proportion_z(x1, n1, x2, n2):
    """Two-sided pooled two-proportion z-test. {"diff": x1/n1 - x2/n2, "z", "p_value"};
    None when a group is empty or the standard error is 0."""
    # TODO
    raise NotImplementedError


def retention_by_segment(users, active, cohort, k, field):
    """{segment: {"size", "active", "rate"}} for one cohort at month k, split by `field` ("source" or "platform")."""
    # TODO
    raise NotImplementedError
