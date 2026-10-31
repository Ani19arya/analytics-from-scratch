"""Solution: grade an LLM ticket classifier by hand, with an honest margin of error."""
import csv
import math
import os

LABELS = ["billing", "bug", "refund", "other"]
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tickets.csv")

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
    """cm[actual][predicted] = count. Actual is the human label."""
    cm = {a: {p: 0 for p in labels} for a in labels}
    for row in rows:
        cm[row["human_label"]][row["llm_label"]] += 1
    return cm


def accuracy(cm):
    total = sum(sum(r.values()) for r in cm.values())
    right = sum(cm[k][k] for k in cm)
    return right / total if total else 0.0


def counts(cm, label):
    """(tp, fp, fn) for one label."""
    tp = cm[label][label]
    fp = sum(cm[a][label] for a in cm if a != label)
    fn = sum(cm[label][p] for p in cm[label] if p != label)
    return tp, fp, fn


def precision_recall_f1(cm, label):
    tp, fp, fn = counts(cm, label)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def wilson_interval(successes, n, z=Z95):
    """95% Wilson score interval for successes out of n. With n = 0 we know nothing: (0.0, 1.0)."""
    if n == 0:
        return 0.0, 1.0
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def meets_rule(precision, recall, min_precision=MIN_PRECISION, min_recall=MIN_RECALL):
    return precision >= min_precision and recall >= min_recall


def decide(cm, label, min_precision=MIN_PRECISION, min_recall=MIN_RECALL):
    """'yes' if both lower bounds clear the bar, 'no' if either upper bound is below it, else 'not proven'."""
    tp, fp, fn = counts(cm, label)
    p_low, p_high = wilson_interval(tp, tp + fp)
    r_low, r_high = wilson_interval(tp, tp + fn)
    if meets_rule(p_low, r_low, min_precision, min_recall):
        return "yes"
    if p_high < min_precision or r_high < min_recall:
        return "no"
    return "not proven"


def main():
    rows = load_rows()
    cm = confusion_matrix(rows, LABELS)
    print("actual \\ predicted".ljust(20) + "".join(l.rjust(9) for l in LABELS))
    for a in LABELS:
        print(a.ljust(20) + "".join(str(cm[a][p]).rjust(9) for p in LABELS))
    print("accuracy %.3f" % accuracy(cm))
    for label in LABELS:
        p, r, f1 = precision_recall_f1(cm, label)
        print("%-8s precision %.3f recall %.3f f1 %.3f" % (label, p, r, f1))
    tp, fp, fn = counts(cm, "refund")
    p_low, p_high = wilson_interval(tp, tp + fp)
    r_low, r_high = wilson_interval(tp, tp + fn)
    print("refund precision %d/%d, 95%% interval %.3f to %.3f (bar %.2f)" % (tp, tp + fp, p_low, p_high, MIN_PRECISION))
    print("refund recall    %d/%d, 95%% interval %.3f to %.3f (bar %.2f)" % (tp, tp + fn, r_low, r_high, MIN_RECALL))
    print("auto-route refunds:", decide(cm, "refund"))


if __name__ == "__main__":
    main()
