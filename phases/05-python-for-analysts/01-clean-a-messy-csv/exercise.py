"""Exercise: clean a messy CSV export with the standard library only.

load_csv, normalize_space and main are done for you. Fill in the functions marked TODO.
Then run: python3 test_lesson.py
"""
import csv
import os
import re
from datetime import datetime

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# The export mixes these. Slashes are day first: the file comes from the India office.
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%b %d, %Y", "%d-%b-%Y"]

# A currency marker, optional spaces, then digits with optional commas and decimals.
# TODO: write the pattern. Group 1 is the marker, group 2 the number.
AMOUNT = None
CURRENCY = {"$": "USD", "USD": "USD", "INR": "INR", "RS": "INR", "RS.": "INR"}


def load_csv(name, data_dir=DATA):
    with open(os.path.join(data_dir, name), newline="") as f:
        return list(csv.DictReader(f))


def normalize_space(value):
    """Strip both ends and collapse runs of inner spaces to one."""
    return " ".join(value.split())


def parse_date(value):
    """Return the date as YYYY-MM-DD, or None if no known format fits."""
    # TODO: try each format in DATE_FORMATS with datetime.strptime.
    raise NotImplementedError

def parse_amount(value):
    """Return (amount as float, 'USD' or 'INR'), or None if it is not a money string."""
    # TODO: match AMOUNT, strip the commas, map the marker with CURRENCY.
    raise NotImplementedError

def clean_rows(raw_rows):
    """Return (clean_rows, report). Rows are checked in a fixed order of reasons."""
    # TODO: normalize every cell, then drop in this order: blank_date, bad_date,
    # blank_amount, bad_amount, duplicate (same cleaned row seen before).
    # Fill a blank city with "Unknown". Report keys: rows_in, rows_out,
    # trimmed_cells, filled_city, dropped (reason -> count), dropped_rows.
    raise NotImplementedError

def main():
    clean, report = clean_rows(load_csv("orders_raw.csv"))
    print("rows in:", report["rows_in"], " rows out:", report["rows_out"])
    print("cells with stray spaces fixed:", report["trimmed_cells"])
    print("blank cities filled with Unknown:", report["filled_city"])
    for reason, n in sorted(report["dropped"].items()):
        print("dropped", reason, n)
    print("first clean row:", clean[0])


if __name__ == "__main__":
    main()
