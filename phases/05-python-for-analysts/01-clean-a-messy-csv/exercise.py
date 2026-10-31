"""Exercise: clean a messy CSV export with the standard library only.

load_csv, normalize_space, totals_by_currency and main are done for you.
Fill in the parts marked TODO. Then run: python3 test_lesson.py
"""
import csv
import os
import re
from datetime import datetime

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# The export mixes these. Slashes are day first: the file comes from the India office.
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%b %d, %Y", "%d-%b-%Y"]

# A currency marker, optional spaces, then a number that starts with a digit.
# Commas may sit between digits; the number may end with a decimal part.
# TODO: write the pattern with re.compile(..., re.IGNORECASE). Group 1 is the marker, group 2 the number.
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
    # TODO: normalize every cell (a missing cell can be None: treat it as ""), then drop in
    # this order: blank_date, bad_date, blank_amount, bad_amount, duplicate (same cleaned
    # row seen before). Fill a blank city with "Unknown".
    # Then, as a second pass: an order_id that still has two different rows is a
    # conflict. Drop every row of it with the reason conflict.
    # Clean row keys: order_id, order_date (YYYY-MM-DD), customer, city, amount (float), currency.
    # Report keys: rows_in, rows_out, trimmed_cells, filled_city,
    # dropped (reason -> count), dropped_rows (list of (order_id, reason)).
    raise NotImplementedError


def totals_by_currency(clean):
    """{currency: (orders, total amount)}. Never adds one currency to another."""
    out = {}
    for r in clean:
        n, total = out.get(r["currency"], (0, 0.0))
        out[r["currency"]] = (n + 1, round(total + r["amount"], 2))
    return dict(sorted(out.items()))


def main():
    clean, report = clean_rows(load_csv("orders_raw.csv"))
    print("rows in:", report["rows_in"], " rows out:", report["rows_out"])
    print("cells with stray spaces fixed:", report["trimmed_cells"])
    print("blank cities filled with Unknown:", report["filled_city"])
    for reason, n in sorted(report["dropped"].items()):
        print("dropped", reason, n)
    print("conflicts to send back:", [oid for oid, reason in report["dropped_rows"] if reason == "conflict"])
    for currency, (n, total) in totals_by_currency(clean).items():
        print("total", currency, n, "orders", format(total, ",.2f"))
    print("first clean row:", clean[0])


if __name__ == "__main__":
    main()
