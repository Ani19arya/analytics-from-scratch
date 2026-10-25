"""Exercise: grade an LLM ticket classifier by hand.

Fill in the four functions marked TODO. Then run: python3 test_lesson.py
"""
import csv
import os

LABELS = ["billing", "bug", "refund", "other"]
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "tickets.csv")

# Business rule from the support lead: auto-route "refund" tickets only if
# precision >= 0.90 and recall >= 0.80 on the labelled sample.
MIN_PRECISION = 0.90
MIN_RECALL = 0.80


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


def precision_recall_f1(cm, label):
    """Return (precision, recall, f1) for one label. Use 0.0 when a denominator is 0."""
    # TODO
    raise NotImplementedError


def meets_rule(precision, recall, min_precision=MIN_PRECISION, min_recall=MIN_RECALL):
    """True only when both thresholds are met (>=)."""
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    rows = load_rows()
    cm = confusion_matrix(rows, LABELS)
    print(cm)
    print(precision_recall_f1(cm, "refund"))
