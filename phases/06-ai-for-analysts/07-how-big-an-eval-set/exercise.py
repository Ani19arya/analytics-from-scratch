"""Exercise: how many labelled tickets an eval needs, for one score and for a comparison.

Fill in the functions marked TODO. The formulas are in the README, section "The idea".
Then run: python3 test_lesson.py
"""
import csv
import math
import os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
Z95 = 1.96          # two-sided 95%
Z_POWER80 = 0.8416  # one-sided z for 80% power


def load_rows(path=os.path.join(DATA, "labelled_tickets.csv")):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def right(row, version):
    return row[version + "_label"] == row["gold_label"]


def wilson_interval(k, n, z=Z95):
    """95% Wilson score interval for k successes out of n. (0.0, 1.0) when n is 0."""
    # TODO
    raise NotImplementedError


def margin(k, n, z=Z95):
    """Half the width of the Wilson interval: the 'plus or minus' you can quote."""
    # TODO
    raise NotImplementedError


def n_for_margin(p, target, z=Z95):
    """Smallest whole n whose Wilson half-width, at an expected rate p, is at most target.

    Raise ValueError unless 0 < target < 0.5.
    """
    # TODO: the half-width shrinks as n grows, so you can search for the first n that is small enough
    raise NotImplementedError


def paired_table(rows, a="v2", b="v3"):
    """(both right, only a right, only b right, both wrong) over the same tickets."""
    # TODO
    raise NotImplementedError


def paired_difference_interval(only_a, only_b, n, z=Z95):
    """95% interval for accuracy(b) - accuracy(a) on n paired tickets. (-1.0, 1.0) when n is 0."""
    # TODO
    raise NotImplementedError


def verdict(rows, a="v2", b="v3"):
    """'v3 better', 'v2 better' or 'not proven' (using the version names passed in).

    b is better only when the whole paired interval is above 0, a only when it is all below 0.
    """
    # TODO
    raise NotImplementedError


def n_for_paired_difference(delta, discordant, z_alpha=Z95, z_beta=Z_POWER80):
    """Tickets needed to detect a true gain delta with 80% power, both versions on the same tickets.

    discordant is the expected share of tickets where exactly one version is right.
    Round up to a whole ticket. Raise ValueError unless 0 < delta <= discordant.
    """
    # TODO
    raise NotImplementedError


def n_for_unpaired_difference(p1, p2, z_alpha=Z95, z_beta=Z_POWER80):
    """Tickets needed PER VERSION if each version is graded on its own separate tickets.

    Round up. Raise ValueError when p1 == p2.
    """
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    rows = load_rows()
    print(paired_table(rows[:50]))
    print(verdict(rows[:50]))
    print(n_for_margin(0.87, 0.02))
