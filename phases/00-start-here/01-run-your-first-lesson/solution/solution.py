"""Lesson 00-01: run your first lesson. Worked answer.

Check it with, from the lesson folder:

    CHECK_SOLUTION=1 python3 test_lesson.py
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def load_orders(path=os.path.join(HERE, "..", "data", "orders.csv")):
    """Read the orders file. Returns one dictionary per order, amount as a number."""
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["amount"] = float(row["amount"])
    return rows


def count_orders(orders):
    """How many orders are in the list?"""
    return len(orders)


def total_amount(orders):
    """What is the total of the amount column, rounded to 2 decimals?"""
    total = 0
    for order in orders:
        total = total + order["amount"]
    return round(total, 2)


if __name__ == "__main__":
    orders = load_orders()
    print("orders:", count_orders(orders))
    print("total:", total_amount(orders))
