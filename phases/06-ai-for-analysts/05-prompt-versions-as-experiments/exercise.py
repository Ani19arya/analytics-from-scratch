"""Exercise: is prompt v2 better than v1 on the same 200 tickets?

Fill in the functions marked TODO. Then run: python3 test_lesson.py
"""
import csv
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
ALPHA = 0.05


def load_csv(name):
    with open(os.path.join(DATA, name), newline="") as f:
        return list(csv.DictReader(f))


def pair_runs(gold_rows, run_a, run_b):
    """Join on ticket_id and return [{"ticket_id", "gold", "a", "b"}], sorted by ticket_id.

    gold_rows have "gold_label"; run_a and run_b have "label".
    Raise ValueError if any file repeats a ticket_id, or if run_a or run_b does not hold
    exactly the same ticket_ids as gold_rows.
    """
    # TODO
    raise NotImplementedError


def accuracy(pairs, key):
    """Share of pairs where pair[key] == pair["gold"]. Return 0.0 for an empty list."""
    # TODO
    raise NotImplementedError


def paired_table(pairs):
    """Return (both right, only a right, only b right, both wrong)."""
    # TODO
    raise NotImplementedError


def exact_two_sided_p(k, n):
    """Two-sided exact binomial p-value for k out of n when each is a coin flip (chance 1/2).

    p = 2 * sum of math.comb(n, i) / 2**n for i from 0 to min(k, n - k), capped at 1.0.
    With n == 0 return 1.0.
    """
    # TODO
    raise NotImplementedError


def compare(pairs, alpha=ALPHA):
    """Return {"n", "acc_a", "acc_b", "a_only", "b_only", "p_value", "verdict"}.

    Only the discordant tickets (one version right, the other wrong) carry evidence:
    p_value = exact_two_sided_p(b_only, a_only + b_only).
    verdict: "v2 better" if p_value < alpha and b_only > a_only,
             "v1 better" if p_value < alpha and a_only > b_only,
             otherwise "no clear difference".
    """
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    pairs = pair_runs(load_csv("tickets.csv"), load_csv("run_v1.csv"), load_csv("run_v2.csv"))
    print(paired_table(pairs))
    print(compare(pairs))
