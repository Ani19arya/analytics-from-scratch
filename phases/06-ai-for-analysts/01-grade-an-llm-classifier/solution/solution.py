"""Solution: grade an LLM ticket classifier by hand."""
import csv
import os

LABELS = ["billing", "bug", "refund", "other"]
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tickets.csv")

# Business rule from the support lead: auto-route "refund" tickets only if
# precision >= 0.90 and recall >= 0.80 on the labelled sample.
MIN_PRECISION = 0.90
MIN_RECALL = 0.80


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


def precision_recall_f1(cm, label):
    tp = cm[label][label]
    fp = sum(cm[a][label] for a in cm if a != label)
    fn = sum(cm[label][p] for p in cm[label] if p != label)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def meets_rule(precision, recall, min_precision=MIN_PRECISION, min_recall=MIN_RECALL):
    return precision >= min_precision and recall >= min_recall


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
    p, r, _ = precision_recall_f1(cm, "refund")
    print("auto-route refunds:", "yes" if meets_rule(p, r) else "no")


if __name__ == "__main__":
    main()
