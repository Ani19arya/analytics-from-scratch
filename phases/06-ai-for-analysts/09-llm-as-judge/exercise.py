"""Exercise: measure whether an LLM judge agrees with people, and find its biases.

Fill in the functions marked TODO. Then run: python3 test_lesson.py
"""
import csv
import os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
LONG = 120  # replies of this many words or more count as long


def load_csv(name):
    with open(os.path.join(DATA, name), newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if "words" in r:
            r["words"] = int(r["words"])
    return rows


def cohen_kappa(a, b):
    """Return (observed agreement, chance agreement, kappa) for two equal-length lists of labels.

    observed = share of items where a and b give the same label.
    chance   = sum over labels of (share of a with that label) x (share of b with that label).
    kappa    = (observed - chance) / (1 - chance).
    kappa is None when chance is 1 (both raters always used one and the same label).
    Raise ValueError if the lists differ in length or are empty.
    """
    # TODO
    raise NotImplementedError


def kappas(rows):
    """Kappa for every pair of graders: A with B, judge with A, judge with B."""
    # TODO
    raise NotImplementedError


def false_pass_by_length(rows, long_words=LONG):
    """Among replies BOTH people failed, how often the judge passed them, split by length.

    Return {"short": (judge passes, replies), "long": (judge passes, replies)}.
    Long means words >= long_words.
    """
    # TODO
    raise NotImplementedError


def position_stats(pairs):
    """How the judge's choice depends on order.

    Each pair was judged twice: judge_x_first (x shown first) and judge_y_first (y shown first),
    each naming the winner, "x" or "y". Return a dict:
    pairs: number of pairs; consistent: pairs where the same reply won in both orders;
    first_wins: verdicts (out of 2 per pair) where the reply shown first won.
    """
    # TODO
    raise NotImplementedError


def swap_verdicts(pairs):
    """One verdict per pair that does not depend on order: the winner if both orders agree, else 'tie'."""
    # TODO
    raise NotImplementedError


def agreement_with_human(pairs, verdicts):
    """(agree, decided): among pairs whose verdict is not 'tie', how many match the person's choice."""
    # TODO
    raise NotImplementedError


def main():
    rows = load_csv("answers.csv")
    pairs = load_csv("pairs.csv")
    for name, value in kappas(rows).items():
        print("kappa %-10s %.3f" % (name, value))
    print("judge passes replies both people failed:", false_pass_by_length(rows))
    print("position:", position_stats(pairs))
    first_only = [p["judge_x_first"] for p in pairs]
    print("x-first verdict agrees with the person:", agreement_with_human(pairs, first_only))
    print("both-orders verdict agrees with the person:", agreement_with_human(pairs, swap_verdicts(pairs)))


if __name__ == "__main__":
    main()
