"""Exercise: choose a confidence threshold on validation tickets, report it on held-out tickets.

Fill in the functions marked TODO. Then run: python3 test_lesson.py
"""
import csv
import math
import os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
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
    # TODO
    raise NotImplementedError


def choose_threshold(rows, target=TARGET_PRECISION, min_auto=MIN_AUTO):
    """The lowest threshold, among the confidences seen, with precision >= target and at least
    min_auto tickets auto-handled. Lowest means the most tickets handled automatically.
    None when no threshold qualifies: then every ticket goes to a person.
    """
    # TODO
    raise NotImplementedError


def report(rows, threshold):
    """What happens on these rows at this threshold, with a 95% interval for precision.

    Return a dict with keys threshold, auto, right, precision, low, high, coverage, to_review.
    precision, low, high and coverage are rounded to 3 places. low and high are the Wilson
    interval for right out of auto. to_review is the number of rows not auto-handled.
    """
    # TODO
    raise NotImplementedError


def calibration(rows, edges):
    """For each bin [edges[i], edges[i+1]) (the last bin includes its top edge): (low, high, n,
    mean reported confidence, share right). Empty bins give None for the two means."""
    # TODO
    raise NotImplementedError


def review_queue(rows, threshold):
    """Tickets below the threshold, counted by the label the LLM gave: who gets which pile."""
    # TODO
    raise NotImplementedError


def review_hours(coverage, weekly=WEEKLY_TICKETS, minutes=MINUTES_PER_REVIEW):
    """Person-hours a week to review everything that is not auto-handled, rounded to 1 place."""
    # TODO
    raise NotImplementedError


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
