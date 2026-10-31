"""Lesson 00-03: tables, rows and grain. Your turn.

Part 1: fill in GRAIN and KEYS for the three tables.
Part 2 to 4: finish the functions marked TODO.

Run, from this folder:

    python3 test_lesson.py
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# Part 1. What one row means, and which columns identify it.
# Open the three files in data/ (or run python3 exercise.py) and look at the columns.
# For GRAIN pick one of: "one row per customer", "one row per order",
#                        "one row per order line", "one row per dish", "one row per day"
GRAIN = {
    "customers": "",     # TODO
    "orders": "",        # TODO
    "order_items": "",   # TODO
}
# For KEYS give the list of column names that should identify one row,
# for example ["customer_id"]. Use the smallest list that works.
KEYS = {
    "customers": [],     # TODO
    "orders": [],        # TODO
    "order_items": [],   # TODO
}


def load(table, folder=os.path.join(HERE, "data")):
    """Read data/<table>.csv as a list of dictionaries. Already written for you. Every value is text."""
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
        # TODO: add 1 to counts[value]. counts.get(value, 0) is the count so far.
    # TODO: return only the values whose count is more than 1.
    return {}


def is_primary_key(rows, key):
    """True if the columns are never blank and no two rows share the same values."""
    # TODO: return False if any row has "" in a key column.
    #       Then return True only if duplicate_keys(rows, key) is empty ({}).
    return False


# Part 3. How two tables relate.
def relationship(left_rows, right_rows, column):
    """"one-to-one", "one-to-many", "many-to-one" or "many-to-many" for a join on one column."""
    left_unique = duplicate_keys(left_rows, [column]) == {}
    right_unique = duplicate_keys(right_rows, [column]) == {}
    # TODO: both unique -> "one-to-one"; only left unique -> "one-to-many";
    #       only right unique -> "many-to-one"; neither -> "many-to-many".
    return ""


# Part 4. Add up at the right grain.
def total_delivery_fees(orders):
    """Sum of delivery_fee, counting each order_id once even if the row is repeated. Rounded to 2 decimals."""
    seen = set()   # the order_ids already added
    total = 0
    for row in orders:
        # TODO: skip the row if row["order_id"] is already in seen.
        #       Otherwise add it to seen (seen.add(...)) and add float(row["delivery_fee"]) to total.
        pass
    return round(total, 2)


if __name__ == "__main__":
    tables = {name: load(name) for name in KEYS}
    for name, rows in tables.items():
        print(name, len(rows), "rows, columns:", list(rows[0]))
    print("repeated orders:", duplicate_keys(tables["orders"], ["order_id"]))
    print("delivery fees:", total_delivery_fees(tables["orders"]))
