"""Lesson 00-02: think like an analyst. Worked answer.

Check it with, from the lesson folder:

    CHECK_SOLUTION=1 python3 test_lesson.py
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# Part 1. The question plan, written before touching the data.
PLAN = {
    "question": "Did completed sales fall in the first four days of this week, compared with the same four days last week, and which city or channel explains the fall?",
    "decision": "Whether Arjun moves delivery riders or a promotion budget to the city that fell, before the weekend.",
    "metric": "completed sales",
    "metric_definition": "Sum of amount for orders with status completed. Cancelled orders are excluded. Rupees.",
    "comparison": {"current": ("2026-10-26", "2026-10-29"), "previous": ("2026-10-19", "2026-10-22")},
    "segments": ["city", "channel"],
    "data_needed": ["order_date", "status", "amount", "city", "channel"],
    "analysis_type": "diagnostic",
}

# Part 2. The four kinds of analysis.
ANALYSIS_TYPES = {
    "How much did we sell last week?": "descriptive",
    "Why did sales fall in one city this week?": "diagnostic",
    "How many orders should we expect next Monday?": "predictive",
    "Should we send a discount coupon to customers in that city?": "prescriptive",
}


def load_rows(path=os.path.join(HERE, "..", "data", "orders.csv")):
    """Read the orders file. Returns one dictionary per order, amount as a number."""
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["amount"] = float(row["amount"])
    return rows


# Part 3. The comparison the clarified question asks for.
def in_period(date, period):
    """True if the date (text such as "2026-10-26") is inside the period, both ends included."""
    start, end = period
    return start <= date <= end


def total_sales(rows, period):
    """Completed sales in the period, rounded to 2 decimals."""
    total = 0
    for row in rows:
        if row["status"] == "completed" and in_period(row["order_date"], period):
            total = total + row["amount"]
    return round(total, 2)


def percent_change(current, previous):
    """Change from previous to current in percent, rounded to 1 decimal. None if previous is 0."""
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


def change_by_segment(rows, column, current, previous):
    """For each value of the column (each city, say): current sales minus previous sales, rounded to 2 decimals."""
    now, before = {}, {}
    for row in rows:
        if row["status"] != "completed":
            continue
        key = row[column]
        if in_period(row["order_date"], current):
            now[key] = now.get(key, 0) + row["amount"]
        elif in_period(row["order_date"], previous):
            before[key] = before.get(key, 0) + row["amount"]
    keys = sorted(set(now) | set(before))
    return {key: round(now.get(key, 0) - before.get(key, 0), 2) for key in keys}


def biggest_drop(changes):
    """The segment with the most negative change. Ties go to the name first in A to Z order. None if nothing fell."""
    worst = None
    for key in sorted(changes):
        if changes[key] < 0 and (worst is None or changes[key] < changes[worst]):
            worst = key
    return worst


if __name__ == "__main__":
    rows = load_rows()
    cur, prev = PLAN["comparison"]["current"], PLAN["comparison"]["previous"]
    now, before = total_sales(rows, cur), total_sales(rows, prev)
    print("current:", now, "previous:", before, "change %:", percent_change(now, before))
    for column in PLAN["segments"]:
        changes = change_by_segment(rows, column, cur, prev)
        print(column, changes, "biggest drop:", biggest_drop(changes))
