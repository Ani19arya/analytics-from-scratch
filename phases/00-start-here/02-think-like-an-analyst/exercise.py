"""Lesson 00-02: think like an analyst. Your turn.

Part 1: fill in PLAN, the questions you would ask Arjun, before any data.
Part 2: label each question in ANALYSIS_TYPES.
Part 3: finish the five small functions marked TODO.

Run, from this folder:

    python3 test_lesson.py
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# Part 1. The question plan. Read "The idea" in README.md first.
# Every value must be filled in. The columns of data/orders.csv are:
#   order_id, order_date, city, channel, status, amount
PLAN = {
    "question": "",            # TODO: the clarified question, in one sentence
    "decision": "",            # TODO: what Arjun will decide with the answer
    "metric": "",              # TODO: the name of the number, such as "completed sales"
    "metric_definition": "",   # TODO: how it is calculated, and what is left out
    "comparison": {            # TODO: dates as "YYYY-MM-DD", first day and last day, both included
        "current": ("", ""),   #   the days of this week that have data
        "previous": ("", ""),  #   the SAME days of last week (like for like)
    },
    "segments": [],            # TODO: the columns you would split the number by (at least two)
    "data_needed": [],         # TODO: every column the analysis uses
    "analysis_type": "",       # TODO: descriptive, diagnostic, predictive or prescriptive
}

# Part 2. Label each question: descriptive, diagnostic, predictive or prescriptive.
ANALYSIS_TYPES = {
    "How much did we sell last week?": "",                              # TODO
    "Why did sales fall in one city this week?": "",                    # TODO
    "How many orders should we expect next Monday?": "",                # TODO
    "Should we send a discount coupon to customers in that city?": "",  # TODO
}


def load_rows(path=os.path.join(HERE, "data", "orders.csv")):
    """Read the orders file. Already written for you. Amount is already a number."""
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["amount"] = float(row["amount"])
    return rows


# Part 3. The comparison the clarified question asks for.
def in_period(date, period):
    """True if the date (text such as "2026-10-26") is inside the period, both ends included."""
    start, end = period
    # TODO: dates written as YYYY-MM-DD sort like dates, so you can compare the text:
    #     return start <= date <= end
    return False


def total_sales(rows, period):
    """Completed sales in the period, rounded to 2 decimals. Cancelled orders do not count."""
    total = 0
    for row in rows:
        # TODO: add row["amount"] to total only if row["status"] is "completed"
        #       and in_period(row["order_date"], period) is True.
        pass
    return round(total, 2)


def percent_change(current, previous):
    """Change from previous to current in percent, rounded to 1 decimal. None if previous is 0."""
    # TODO: if previous is 0, return None (you cannot divide by zero).
    #       Otherwise return round((current - previous) / previous * 100, 1)
    return 0


def change_by_segment(rows, column, current, previous):
    """For each value of the column (each city, say): current sales minus previous sales, rounded to 2 decimals.

    Example: change_by_segment(rows, "city", cur, prev) -> {"Mumbai": 1992.32, ...}
    Only completed orders count. A value that appears in only one period still gets a row.
    """
    now = {}     # city -> completed sales in the current period
    before = {}  # city -> completed sales in the previous period
    for row in rows:
        if row["status"] != "completed":
            continue
        key = row[column]
        # TODO: if the order is in the current period, add its amount to now[key].
        #       If it is in the previous period, add its amount to before[key].
        #       now.get(key, 0) gives the running total so far, or 0 the first time.
    keys = sorted(set(now) | set(before))
    return {key: round(now.get(key, 0) - before.get(key, 0), 2) for key in keys}


def biggest_drop(changes):
    """The segment with the most negative change. Ties go to the name first in A to Z order.

    Returns None if no segment fell.
    """
    worst = None
    for key in sorted(changes):
        # TODO: if changes[key] is below 0, and worst is None or changes[key] < changes[worst],
        #       then set worst = key.
        pass
    return worst


if __name__ == "__main__":
    rows = load_rows()
    cur, prev = PLAN["comparison"]["current"], PLAN["comparison"]["previous"]
    now, before = total_sales(rows, cur), total_sales(rows, prev)
    print("current:", now, "previous:", before, "change %:", percent_change(now, before))
    for column in PLAN["segments"]:
        changes = change_by_segment(rows, column, cur, prev)
        print(column, changes, "biggest drop:", biggest_drop(changes))
