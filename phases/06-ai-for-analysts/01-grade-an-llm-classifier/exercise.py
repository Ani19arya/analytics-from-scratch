"""Exercise: grade an LLM ticket classifier by hand, with an honest margin of error.

Fill in the functions marked TODO. Then run: python3 test_lesson.py
"""
import csv
import math
import os

LABELS = ["billing", "bug", "refund", "other"]
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "tickets.csv")

# Business rule from the support lead: auto-route "refund" tickets only if
# precision >= 0.90 and recall >= 0.80. Because 400 tickets is a sample, the
# rule is applied to the LOWER end of each 95% interval, not to the point value.
MIN_PRECISION = 0.90
MIN_RECALL = 0.80
Z95 = 1.96


def load_rows(path=DATA):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def confusion_matrix(rows, labels):
    """Return cm[actual][predicted] = count, with every label present as a key.

    Actual is row["human_label"], predicted is row["llm_label"].
    """
    # TODO
    raise NotImplementedError


def accuracy(cm):
    """Share of all tickets on the diagonal. Return 0.0 for an empty matrix."""
    # TODO
    raise NotImplementedError


def counts(cm, label):
    """Return (tp, fp, fn) for one label.

    tp: actual label, predicted label. fp: predicted label, actually something else.
    fn: actual label, predicted something else.
    """
    # TODO
    raise NotImplementedError


def precision_recall_f1(cm, label):
    """Return (precision, recall, f1) for one label. Use 0.0 when a denominator is 0."""
    # TODO: use counts()
    raise NotImplementedError


def wilson_interval(successes, n, z=Z95):
    """Return (low, high), the Wilson score interval for successes out of n.

    p = successes / n
    centre = (p + z^2 / (2n)) / (1 + z^2 / n)
    half   = z * sqrt(p(1 - p) / n + z^2 / (4n^2)) / (1 + z^2 / n)
    Return (centre - half, centre + half). With n = 0 return (0.0, 1.0).
    """
    # TODO
    raise NotImplementedError


def meets_rule(precision, recall, min_precision=MIN_PRECISION, min_recall=MIN_RECALL):
    """True only when both thresholds are met (>=)."""
    # TODO
    raise NotImplementedError


def decide(cm, label, min_precision=MIN_PRECISION, min_recall=MIN_RECALL):
    """Return 'yes', 'no' or 'not proven'.

    'yes' if the LOWER bounds of the precision and recall intervals both meet the bar
    (use meets_rule). 'no' if either UPPER bound is below its bar. Otherwise 'not proven'.
    """
    # TODO: precision is tp out of tp + fp, recall is tp out of tp + fn
    raise NotImplementedError


if __name__ == "__main__":
    rows = load_rows()
    cm = confusion_matrix(rows, LABELS)
    print(cm)
    print(precision_recall_f1(cm, "refund"))
    print(decide(cm, "refund"))
