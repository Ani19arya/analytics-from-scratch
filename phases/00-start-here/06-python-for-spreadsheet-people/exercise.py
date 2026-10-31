"""Lesson 00-06: Python for spreadsheet people. Your turn.

Finish the five functions marked TODO, in order. Then run, from this folder:

    python3 test_lesson.py

Try your functions as you go with: python3 exercise.py
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "purchases.csv")
MISSING = ("", "n/a", "-")


def read_rows(path=DATA):
    """Read a CSV file into a list of rows. Each row is a dictionary: column name -> cell text."""
    # TODO: open the file and return list(csv.DictReader(f)):
    #     with open(path, newline="") as f:
    #         return list(csv.DictReader(f))
    return []


def to_number(text):
    """Turn one typed cell into a number, or None if it is blank or not a number.

    "1,250.00" -> 1250.0   " 300 " -> 300.0   "Rs 450" -> 450.0   "-120.00" -> -120.0
    "" -> None   "n/a" -> None   "92O" (letter O) -> None
    """
    # TODO, step by step:
    # 1. text = text.strip()                       removes spaces at both ends
    # 2. if text.lower().startswith("rs"):         drop the "Rs" and strip again:
    #        text = text[2:].strip()
    # 3. text = text.replace(",", "")              removes thousands commas
    # 4. if text.lower() in MISSING: return None   blank, n/a or - means no value
    # 5. try:
    #        return float(text)
    #    except ValueError:                        anything else that is not a number
    #        return None
    return float(text)


def total(rows, column):
    """Like =SUM(column): adds every cell that is a number, rounded to 2 decimals."""
    result = 0
    for row in rows:
        value = to_number(row[column])
        # TODO: if value is not None, add it to result.
    return round(result, 2)


def count_numbers(rows, column):
    """Like =COUNT(column): how many cells are numbers. A 0 counts; a blank does not."""
    n = 0
    # TODO: loop over rows; add 1 to n when to_number(row[column]) is not None.
    return n


def sumif(rows, column, criteria_column, criteria_value):
    """Like =SUMIF(criteria_column, criteria_value, column). Matching ignores case and extra spaces.

    Example: sumif(rows, "amount", "category", "vegetables") adds the amount of every row
    whose category is "vegetables", "Vegetables", "VEGETABLES" or "vegetables ".
    """
    wanted = criteria_value.strip().lower()
    result = 0
    # TODO: loop over rows. If row[criteria_column].strip().lower() == wanted,
    #       add to_number(row[column]) to result (skip it when it is None).
    return round(result, 2)


def bad_values(rows, column):
    """Already written for you. Cells that are not blank and not "n/a" but still are not numbers.

    Returns [(line in the file, text), ...]. The header is line 1, so the first
    data row is line 2, as in a spreadsheet.
    """
    out = []
    for line, row in enumerate(rows, start=2):
        text = row[column]
        if to_number(text) is None and text.strip().lower() not in MISSING:
            out.append((line, text))
    return out


if __name__ == "__main__":
    rows = read_rows()
    print("rows:", len(rows))
    print("total:", total(rows, "amount"))
    print("numbers:", count_numbers(rows, "amount"))
    print("vegetables:", sumif(rows, "amount", "category", "vegetables"))
    print("to check:", bad_values(rows, "amount"))
