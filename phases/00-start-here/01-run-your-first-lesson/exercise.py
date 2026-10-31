"""Lesson 00-01: run your first lesson. Your turn.

Fill in the two functions marked TODO, then run, from this folder:

    python3 test_lesson.py

(On Windows, type python or py instead of python3.)

The test fails until both functions are right. That is how every lesson works.
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def load_orders(path=os.path.join(HERE, "data", "orders.csv")):
    """Read the orders file. Already written for you.

    Returns a list with one dictionary per order, for example
    {"order_id": "1001", "dish": "masala dosa", "amount": 387.87}.
    The amount is already a number.
    """
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["amount"] = float(row["amount"])
    return rows


def count_orders(orders):
    """How many orders are in the list?"""
    # TODO: return the number of orders. Hint: len(orders) counts the items in a list.
    return 0


def total_amount(orders):
    """What is the total of the amount column, rounded to 2 decimals?"""
    total = 0
    # TODO: loop over the orders and add each order's amount to total:
    #     for order in orders:
    #         total = total + order["amount"]
    return round(total, 2)


if __name__ == "__main__":
    orders = load_orders()
    print("orders:", count_orders(orders))
    print("total:", total_amount(orders))
