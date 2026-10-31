"""Solution: choose a confidence threshold on validation tickets, report it on held-out tickets."""
import csv
import math
import os

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TARGET_PRECISION = 0.95
MIN_AUTO = 50               # never trust a threshold that auto-handles fewer tickets than this
WEEKLY_TICKETS = 2500       # Northwind Desk's weekly volume (fictional)
MINUTES_PER_REVIEW = 3      # how long a person takes to check one ticket (fictional)


def load_rows(split=None, path=os.path.join(DATA, "tickets.csv")):
    """Rows with confidence as a float. split='validation' or 'heldout' keeps one split."""
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["confidence"] = float(r["confidence"])
    if split is not None:
        rows = [r for r in rows if r["split"] == split]
    return rows


def wilson_interval(k, n, z=1.96):
    """95% Wilson score interval for k successes out of n. (0.0, 1.0) when n is 0."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return centre - half, centre + half


def at_threshold(rows, threshold):
    """(auto-handled, right among them, precision, coverage) when confidence >= threshold is automatic.

    precision is 0.0 when nothing is auto-handled; coverage is 0.0 when there are no rows.
    """
    auto = [r for r in rows if r["confidence"] >= threshold]
    right = sum(1 for r in auto if r["llm_label"] == r["gold_label"])
    precision = right / len(auto) if auto else 0.0
    coverage = len(auto) / len(rows) if rows else 0.0
    return len(auto), right, precision, coverage


def choose_threshold(rows, target=TARGET_PRECISION, min_auto=MIN_AUTO):
    """The lowest threshold, among the confidences seen, with precision >= target and at least
    min_auto tickets auto-handled. Lowest means the most tickets handled automatically.
    None when no threshold qualifies: then every ticket goes to a person.
    """
    for t in sorted({r["confidence"] for r in rows}):
        n_auto, _, precision, _ = at_threshold(rows, t)
        if n_auto >= min_auto and precision >= target:
            return t
    return None


def report(rows, threshold):
    """What happens on these rows at this threshold, with a 95% interval for precision.

    Return a dict with keys threshold, auto, right, precision, low, high, coverage, to_review.
    precision, low, high and coverage are rounded to 3 places. low and high are the Wilson
    interval for right out of auto. to_review is the number of rows not auto-handled.
    """
    n_auto, right, precision, coverage = at_threshold(rows, threshold)
    low, high = wilson_interval(right, n_auto)
    return {"threshold": threshold, "auto": n_auto, "right": right, "precision": round(precision, 3),
            "low": round(low, 3), "high": round(high, 3), "coverage": round(coverage, 3),
            "to_review": len(rows) - n_auto}


def calibration(rows, edges):
    """For each bin [edges[i], edges[i+1]) (the last bin includes its top edge): (low, high, n,
    mean reported confidence, share right). Empty bins give None for the two means."""
    out = []
    for i in range(len(edges) - 1):
        low, high = edges[i], edges[i + 1]
        last = i == len(edges) - 2
        part = [r for r in rows if low <= r["confidence"] < high or (last and r["confidence"] == high)]
        if part:
            mean_conf = sum(r["confidence"] for r in part) / len(part)
            acc = sum(1 for r in part if r["llm_label"] == r["gold_label"]) / len(part)
            out.append((low, high, len(part), round(mean_conf, 3), round(acc, 3)))
        else:
            out.append((low, high, 0, None, None))
    return out


def review_queue(rows, threshold):
    """Tickets below the threshold, counted by the label the LLM gave: who gets which pile."""
    counts = {}
    for r in rows:
        if r["confidence"] < threshold:
            counts[r["llm_label"]] = counts.get(r["llm_label"], 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def review_hours(coverage, weekly=WEEKLY_TICKETS, minutes=MINUTES_PER_REVIEW):
    """Person-hours a week to review everything that is not auto-handled, rounded to 1 place."""
    return round(weekly * (1 - coverage) * minutes / 60, 1)


def main():
    val = load_rows("validation")
    held = load_rows("heldout")
    t = choose_threshold(val)
    print("chosen on validation:", t)
    print("validation:", report(val, t))
    print("held-out:  ", report(held, t))
    print("review queue on held-out by LLM label:", review_queue(held, t))
    print("review hours a week:", review_hours(report(held, t)["coverage"]))


if __name__ == "__main__":
    main()
