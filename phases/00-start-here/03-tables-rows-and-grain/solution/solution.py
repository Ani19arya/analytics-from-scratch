"""Lesson 00-03: tables, rows and grain. Worked answer.

Check it with, from the lesson folder:

    CHECK_SOLUTION=1 python3 test_lesson.py
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# Part 1. What one row means, and which columns identify it.
GRAIN = {
    "customers": "one row per customer",
    "orders": "one row per order",
    "order_items": "one row per order line",
}
KEYS = {
    "customers": ["customer_id"],
    "orders": ["order_id"],
    "order_items": ["order_id", "line_no"],
}


def load(table, folder=os.path.join(HERE, "..", "data")):
    """Read data/<table>.csv as a list of dictionaries. Every value is text."""
    with open(os.path.join(folder, table + ".csv"), newline="") as f:
        return list(csv.DictReader(f))


# Part 2. Check keys.
def duplicate_keys(rows, key):
    """Key values that appear more than once, with how often: {("7022",): 2, ...}.

    key is a list of column names. Each key value is a tuple, even for one column.
    """
    counts = {}
    for row in rows:
        value = tuple(row[col] for col in key)
        counts[value] = counts.get(value, 0) + 1
    return {value: n for value, n in counts.items() if n > 1}


def is_primary_key(rows, key):
    """True if the columns are never blank and no two rows share the same values."""
    for row in rows:
        for col in key:
            if row[col] == "":
                return False
    return duplicate_keys(rows, key) == {}


# Part 3. How two tables relate.
def relationship(left_rows, right_rows, column):
    """"one-to-one", "one-to-many", "many-to-one" or "many-to-many" for a join on one column."""
    left_unique = duplicate_keys(left_rows, [column]) == {}
    right_unique = duplicate_keys(right_rows, [column]) == {}
    if left_unique and right_unique:
        return "one-to-one"
    if left_unique:
        return "one-to-many"
    if right_unique:
        return "many-to-one"
    return "many-to-many"


# Part 4. Add up at the right grain.
def total_delivery_fees(orders):
    """Sum of delivery_fee, counting each order_id once even if the row is repeated. Rounded to 2 decimals."""
    seen = set()
    total = 0
    for row in orders:
        if row["order_id"] in seen:
            continue
        seen.add(row["order_id"])
        total = total + float(row["delivery_fee"])
    return round(total, 2)


if __name__ == "__main__":
    tables = {name: load(name) for name in KEYS}
    for name, rows in tables.items():
        print(name, len(rows), "rows,", GRAIN[name], "| key", KEYS[name], "unique:", is_primary_key(rows, KEYS[name]))
    print("repeated orders:", duplicate_keys(tables["orders"], ["order_id"]))
    print("customers to orders:", relationship(tables["customers"], tables["orders"], "customer_id"))
    print("orders to order_items:", relationship(tables["orders"], tables["order_items"], "order_id"))
    print("delivery fees:", total_delivery_fees(tables["orders"]))
